"""Port forwarding action for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

from asusrouter.modules.action import ARAction
from asusrouter.modules.common.command import ARService
from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.port_forwarding.enums import (
    ARPortForwardingCommand,
    ARPortForwardingField,
    ARPortForwardingProtocol,
)
from asusrouter.modules.port_forwarding.source import (
    ARPortForwardingSourceUniversal,
    serialize_rules,
)
from asusrouter.modules.service.action import (
    ARServiceResult,
    async_run_service,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.identifiers.ip import IpAddress, IpInterface
from asusrouter.tools.types import ARCallbackType

_LOGGER = logging.getLogger(__name__)

# A rule shares the shape the read source emits, for a clean round-trip
ARPortForwardingRule = dict[ARPortForwardingField, Any]

# nvram rule-list key per WAN unit
_LIST_KEYS = {
    0: ARNvramType.PORT_FORWARDING_LIST.value,
    1: ARNvramType.PORT_FORWARDING_LIST_SECONDARY.value,
}


@dataclass(eq=False, repr=False, kw_only=True)
class ARPortForwardingAction(ARAction):
    """Mutate port forwarding rules or the master toggle."""

    command: ARPortForwardingCommand
    state: bool | None = None
    # ADD: rules to append. SET: the full replacement list. Both require
    # complete rules. REMOVE: match specs - a current rule is dropped when a
    # spec matches it on every field the spec sets, so a full read rule is an
    # exact match and a partial one (e.g. `{INTERNAL_IP: ...}`) is a wildcard
    rules: list[ARPortForwardingRule] = field(default_factory=list)


# Rule fields with a defined value when absent from a rule dict
_FIELD_DEFAULTS: dict[ARPortForwardingField, Any] = {
    ARPortForwardingField.WAN_UNIT: 0,
}


def _norm(field_: ARPortForwardingField, value: Any) -> str:
    """Normalize a rule field to a comparable string."""

    if field_ is ARPortForwardingField.PROTOCOL:
        return str(ARPortForwardingProtocol.from_value(value))
    if field_ is ARPortForwardingField.INTERNAL_IP:
        ip = IpAddress.from_value_safe(value)
        return str(ip) if ip is not None else str(value)
    if field_ is ARPortForwardingField.SOURCE_IP:
        iface = IpInterface.from_value_safe(value)
        return str(iface) if iface is not None else str(value)
    return "" if value is None else str(value)


def _spec_matches(
    spec: ARPortForwardingRule, rule: ARPortForwardingRule
) -> bool:
    """Whether a rule matches a spec on every field the spec sets."""

    if not spec:
        # An empty spec must not match everything
        return False
    return all(
        _norm(field_, value)
        == _norm(field_, rule.get(field_, _FIELD_DEFAULTS.get(field_)))
        for field_, value in spec.items()
    )


def _dedup_key(rule: ARPortForwardingRule) -> tuple[Any, ...]:
    """Device identity of a rule: two with the same key forward the same port.

    Mirrors the web UI's duplicate check - name, internal IP and internal port
    are not part of it, since one external port maps to a single forward.
    """

    protocol = ARPortForwardingProtocol.from_value(
        rule.get(ARPortForwardingField.PROTOCOL)
    )
    if protocol is ARPortForwardingProtocol.OTHER:
        external = rule.get(ARPortForwardingField.PROTOCOL_NUMBER)
    else:
        external = rule.get(ARPortForwardingField.EXTERNAL_PORT)

    return (
        rule.get(ARPortForwardingField.WAN_UNIT, 0),
        str(protocol),
        "" if external is None else str(external),
        _norm(
            ARPortForwardingField.SOURCE_IP,
            rule.get(ARPortForwardingField.SOURCE_IP),
        ),
    )


def _dedup(
    rules: list[ARPortForwardingRule],
) -> list[ARPortForwardingRule]:
    """Drop duplicate rules, keeping the first occurrence of each."""

    seen: set[tuple[Any, ...]] = set()
    unique: list[ARPortForwardingRule] = []
    for rule in rules:
        key = _dedup_key(rule)
        if key in seen:
            continue
        seen.add(key)
        unique.append(rule)
    return unique


def _is_complete(rule: ARPortForwardingRule) -> bool:
    """Whether a rule carries the fields the device needs to store it."""

    protocol = ARPortForwardingProtocol.from_value(
        rule.get(ARPortForwardingField.PROTOCOL)
    )
    if protocol is ARPortForwardingProtocol.UNKNOWN:
        return False
    if rule.get(ARPortForwardingField.INTERNAL_IP) is None:
        return False
    if protocol is ARPortForwardingProtocol.OTHER:
        return rule.get(ARPortForwardingField.PROTOCOL_NUMBER) is not None
    return bool(rule.get(ARPortForwardingField.EXTERNAL_PORT))


def _units(rules: list[ARPortForwardingRule]) -> set[int]:
    """Collect the WAN units referenced by a rule list."""

    return {rule.get(ARPortForwardingField.WAN_UNIT, 0) for rule in rules}


def _by_unit(
    rules: list[ARPortForwardingRule], unit: int
) -> list[ARPortForwardingRule]:
    """Filter rules belonging to a WAN unit."""

    return [
        rule
        for rule in rules
        if rule.get(ARPortForwardingField.WAN_UNIT, 0) == unit
    ]


def _state_arguments(action: ARPortForwardingAction) -> dict[str, Any] | None:
    """Build the arguments for a master toggle."""

    if action.state is None:
        return None
    return {ARNvramType.PORT_FORWARDING_STATE.value: int(action.state)}


async def _fetch_rules(
    get_data_callback: ARCallbackType | None,
) -> list[ARPortForwardingRule] | None:
    """Read the current rules, or None when they cannot be fetched."""

    if get_data_callback is None:
        return None
    fetched = await get_data_callback(ARPortForwardingSourceUniversal)
    if not isinstance(fetched, dict):
        return None
    data = fetched.get(ARPortForwardingSourceUniversal) or {}
    return list(data.get(ARPortForwardingField.RULES, []))


async def _rules_arguments(
    action: ARPortForwardingAction,
    get_data_callback: ARCallbackType | None,
) -> dict[str, Any] | None:
    """Build the arguments for an add/remove/set of rules."""

    if action.command is ARPortForwardingCommand.SET:
        # Refuse to write a list containing an incomplete rule
        if not all(_is_complete(rule) for rule in action.rules):
            _LOGGER.debug("SET rejected: an incomplete rule was given")
            return None
        final = list(action.rules)
        # Always rewrite the primary list, so an empty set clears it
        touched = _units(final) | {0}
    elif action.command is ARPortForwardingCommand.ADD:
        if not action.rules or not all(
            _is_complete(rule) for rule in action.rules
        ):
            _LOGGER.debug("ADD rejected: no rules or an incomplete one given")
            return None
        current = await _fetch_rules(get_data_callback)
        if current is None:
            return None
        final = current + list(action.rules)
        touched = _units(current) | _units(final)
    else:  # REMOVE
        specs = [spec for spec in action.rules if spec]
        if not specs:
            _LOGGER.debug("REMOVE rejected: no match specs given")
            return None
        current = await _fetch_rules(get_data_callback)
        if current is None:
            return None
        final = [
            rule
            for rule in current
            if not any(_spec_matches(spec, rule) for spec in specs)
        ]
        # Include emptied units so a full removal still clears them
        touched = _units(current) | _units(final)

    # Collapse duplicates: an added rule already present, or stale doubles
    # left in the saved list
    final = _dedup(final)

    return {
        _LIST_KEYS[unit]: serialize_rules(_by_unit(final, unit))
        for unit in sorted(touched)
        if unit in _LIST_KEYS
    }


async def run_action(
    callback: ARCallbackType,
    action: ARPortForwardingAction,
    *,
    get_data_callback: ARCallbackType | None = None,
    raw_callback: ARCallbackType | None = None,
    expire_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> ARServiceResult:
    """Apply the port forwarding action via `restart_firewall`."""

    if action.command is ARPortForwardingCommand.STATE:
        arguments = _state_arguments(action)
    elif action.command in (
        ARPortForwardingCommand.ADD,
        ARPortForwardingCommand.REMOVE,
        ARPortForwardingCommand.SET,
    ):
        arguments = await _rules_arguments(action, get_data_callback)
    else:
        _LOGGER.debug("Unknown port forwarding command: %s", action.command)
        return ARServiceResult(success=False)

    if not arguments:
        return ARServiceResult(success=False)

    result = await async_run_service(
        callback,
        ARService.FIREWALL_RESTART,
        arguments=arguments,
        raw_callback=raw_callback,
    )

    # Drop the now-stale cached rules/state so the next read refetches
    if result.success and expire_callback is not None:
        await expire_callback(ARPortForwardingSourceUniversal)

    return result


ARCallReg.register_action(ARPortForwardingAction, run_action=run_action)


__all__ = [
    "ARPortForwardingAction",
    "ARPortForwardingRule",
    "run_action",
]
