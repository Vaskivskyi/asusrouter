"""Parental control action for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import TYPE_CHECKING, Any

from asusrouter.modules.action import ARAction
from asusrouter.modules.common.command import ARService
from asusrouter.modules.nvram import ARNvramType, async_expire_values
from asusrouter.modules.parental_control.enums import (
    ARParentalControlCommand,
    ARParentalControlField,
    ARParentalControlScheduleMode,
    ARParentalControlType,
)
from asusrouter.modules.parental_control.schedule.source import (
    PC_REQUEST,
    ARParentalControlSourceUniversal,
    rule_entry_count,
    rule_schedule_mode,
    serialize_rules,
)
from asusrouter.modules.service.action import (
    ARServiceResult,
    async_run_service,
)
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.modules.support.helpers import support_value
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters.raw import raw_to_int
from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.types import ARCallbackType

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity

_LOGGER = logging.getLogger(__name__)

# A rule shares the shape the read source emits, for a clean round-trip
ARParentalControlRule = dict[ARParentalControlField, Any]

# Rule count the device falls back to when `MaxRule_parentctrl` is absent
DEFAULT_MAX_RULES = 16

# Total schedule windows the device falls back to for `MaxRule_PC_DAYTIME`
DEFAULT_MAX_ENTRIES = 128

# Minimum `PC_SCHED_V3` support for the online (allow-only) schedule mode
SCHEDULE_MODE_MIN_VERSION = 3


@dataclass(eq=False, repr=False, kw_only=True)
class ARParentalControlAction(ARAction):
    """Mutate parental control rules or a master toggle."""

    command: ARParentalControlCommand
    state: bool | None = None
    # ADD: rules to append. SET: the full replacement list. Both require
    # complete rules. REMOVE: match specs - a current rule is dropped when a
    # spec matches it on every field the spec sets, so a full read rule is an
    # exact match and a partial one (e.g. `{MAC: ...}`) is a wildcard
    rules: list[ARParentalControlRule] = field(default_factory=list)


def _norm(field_: ARParentalControlField, value: Any) -> str:
    """Normalize a rule field to a comparable string."""

    if field_ is ARParentalControlField.MAC:
        mac = MacAddress.from_value_safe(value)
        return str(mac) if mac is not None else str(value)
    if field_ is ARParentalControlField.TYPE:
        return str(ARParentalControlType.from_value(value))
    return "" if value is None else str(value)


def _spec_matches(
    spec: ARParentalControlRule, rule: ARParentalControlRule
) -> bool:
    """Whether a rule matches a spec on every field the spec sets."""

    if not spec:
        # An empty spec must not match everything
        return False
    return all(
        _norm(field_, value) == _norm(field_, rule.get(field_))
        for field_, value in spec.items()
    )


def _dedup_key(rule: ARParentalControlRule) -> str:
    """Device identity of a rule: one rule per MAC, mirroring the web UI."""

    return _norm(
        ARParentalControlField.MAC, rule.get(ARParentalControlField.MAC)
    )


def _dedup(
    rules: list[ARParentalControlRule],
) -> list[ARParentalControlRule]:
    """Drop duplicate rules, keeping the first occurrence of each MAC."""

    seen: set[str] = set()
    unique: list[ARParentalControlRule] = []
    for rule in rules:
        key = _dedup_key(rule)
        if key in seen:
            continue
        seen.add(key)
        unique.append(rule)
    return unique


def _is_complete(rule: ARParentalControlRule) -> bool:
    """Whether a rule carries the fields the device needs to store it."""

    if (
        MacAddress.from_value_safe(rule.get(ARParentalControlField.MAC))
        is None
    ):
        return False
    type_ = ARParentalControlType.from_value(
        rule.get(ARParentalControlField.TYPE)
    )
    return type_ is not ARParentalControlType.UNKNOWN


def _toggle_arguments(
    action: ARParentalControlAction,
) -> dict[str, Any] | None:
    """Build the arguments for the rules-engine master toggle."""

    if action.state is None:
        return None
    return {ARNvramType.PARENTAL_CONTROL_STATE.value: int(action.state)}


def _max_rules(identity: ARDeviceIdentity | None) -> int:
    """Resolve the device's rule limit, or the firmware default."""

    if identity is not None:
        value = raw_to_int(
            support_value(
                identity.support, ARSupportType.PARENTAL_CONTROL_MAX_RULES
            )
        )
        if value:
            return value
    return DEFAULT_MAX_RULES


def _max_entries(identity: ARDeviceIdentity | None) -> int:
    """Resolve the device's total schedule-window limit, or the default."""

    if identity is not None:
        value = raw_to_int(
            support_value(
                identity.support, ARSupportType.PARENTAL_CONTROL_MAX_ENTRIES
            )
        )
        if value:
            return value
    return DEFAULT_MAX_ENTRIES


def _online_supported(identity: ARDeviceIdentity | None) -> bool:
    """Whether the device accepts the online (allow-only) schedule mode."""

    if identity is None:
        return False
    version = raw_to_int(
        support_value(
            identity.support, ARSupportType.PARENTAL_CONTROL_SCHED_VERSION
        )
    )
    return version is not None and version >= SCHEDULE_MODE_MIN_VERSION


def _modes_supported(
    rules: list[ARParentalControlRule], identity: ARDeviceIdentity | None
) -> bool:
    """Whether every online-mode rule is allowed on this device."""

    if _online_supported(identity):
        return True
    return all(
        rule_schedule_mode(rule) is not ARParentalControlScheduleMode.ONLINE
        for rule in rules
    )


async def _fetch_rules(
    fetch_data_callback: ARCallbackType | None,
) -> list[ARParentalControlRule] | None:
    """Read the current rules, or None when they cannot be fetched."""

    if fetch_data_callback is None:
        return None
    fetched = await fetch_data_callback(ARParentalControlSourceUniversal)
    if not isinstance(fetched, dict):
        return None
    data = fetched.get(ARParentalControlSourceUniversal) or {}
    return list(data.get(ARParentalControlField.RULES, []))


def _resolve_set(
    action: ARParentalControlAction,
) -> list[ARParentalControlRule] | None:
    """Return the SET replacement list, or None if a rule is incomplete."""

    if not all(_is_complete(rule) for rule in action.rules):
        _LOGGER.debug("SET rejected: an incomplete rule was given")
        return None
    return list(action.rules)


async def _resolve_add(
    action: ARParentalControlAction,
    fetch_data_callback: ARCallbackType | None,
) -> list[ARParentalControlRule] | None:
    """Return current rules with the new ones prepended, or None to reject."""

    if not action.rules or not all(
        _is_complete(rule) for rule in action.rules
    ):
        _LOGGER.debug("ADD rejected: no rules or an incomplete one given")
        return None
    current = await _fetch_rules(fetch_data_callback)
    if current is None:
        return None
    # An added MAC replaces the existing rule for that MAC
    return list(action.rules) + current


async def _resolve_remove(
    action: ARParentalControlAction,
    fetch_data_callback: ARCallbackType | None,
) -> list[ARParentalControlRule] | None:
    """Return current rules minus those matching a spec, or None to reject."""

    specs = [spec for spec in action.rules if spec]
    if not specs:
        _LOGGER.debug("REMOVE rejected: no match specs given")
        return None
    current = await _fetch_rules(fetch_data_callback)
    if current is None:
        return None
    return [
        rule
        for rule in current
        if not any(_spec_matches(spec, rule) for spec in specs)
    ]


async def _resolve_rules(
    action: ARParentalControlAction,
    fetch_data_callback: ARCallbackType | None,
) -> list[ARParentalControlRule] | None:
    """Resolve the final rule list for an add/remove/set, or None to reject."""

    if action.command is ARParentalControlCommand.SET:
        return _resolve_set(action)
    if action.command is ARParentalControlCommand.ADD:
        return await _resolve_add(action, fetch_data_callback)
    return await _resolve_remove(action, fetch_data_callback)


async def _rules_arguments(
    action: ARParentalControlAction,
    fetch_data_callback: ARCallbackType | None,
    identity: ARDeviceIdentity | None,
) -> dict[str, Any] | None:
    """Build the arguments for an add/remove/set of rules."""

    resolved = await _resolve_rules(action, fetch_data_callback)
    if resolved is None:
        return None

    # Collapse duplicates, keeping the first rule per MAC
    final = _dedup(resolved)

    # REMOVE only shrinks the list and keeps existing rules as-is
    if action.command is ARParentalControlCommand.REMOVE:
        return serialize_rules(final)

    # ADD/SET introduce rules: reject an online-mode rule the device rejects
    if not _modes_supported(action.rules, identity):
        _LOGGER.debug(
            "%s rejected: online schedule mode is unsupported", action.command
        )
        return None

    # The device rejects a list longer than its rule limit
    limit = _max_rules(identity)
    if len(final) > limit:
        _LOGGER.debug(
            "%s rejected: %d rules exceed the limit of %d",
            action.command,
            len(final),
            limit,
        )
        return None

    # The device also caps the total schedule windows across every rule
    entries = sum(rule_entry_count(rule) for rule in final)
    entry_limit = _max_entries(identity)
    if entries > entry_limit:
        _LOGGER.debug(
            "%s rejected: %d schedule windows exceed the limit of %d",
            action.command,
            entries,
            entry_limit,
        )
        return None

    return serialize_rules(final)


async def run_action(
    callback: ARCallbackType,
    action: ARParentalControlAction,
    *,
    fetch_data_callback: ARCallbackType | None = None,
    fetch_raw_callback: ARCallbackType | None = None,
    expire_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> ARServiceResult:
    """Apply the parental control action via `restart_firewall`."""

    identity: ARDeviceIdentity | None = kwargs.get("identity")

    if action.command is ARParentalControlCommand.STATE:
        arguments = _toggle_arguments(action)
    elif action.command in (
        ARParentalControlCommand.ADD,
        ARParentalControlCommand.REMOVE,
        ARParentalControlCommand.SET,
    ):
        arguments = await _rules_arguments(
            action, fetch_data_callback, identity
        )
    else:
        _LOGGER.debug("Unknown parental control command: %s", action.command)
        return ARServiceResult(success=False)

    if not arguments:
        return ARServiceResult(success=False)

    result = await async_run_service(
        callback,
        ARService.FIREWALL_RESTART,
        arguments=arguments,
        fetch_raw_callback=fetch_raw_callback,
    )

    # Drop the now-stale cached rules/state so the next read refetches
    if result.success and expire_callback is not None:
        await expire_callback(ARParentalControlSourceUniversal)
        await async_expire_values(expire_callback, PC_REQUEST)

    return result


ARCallReg.register_action(ARParentalControlAction, run_action=run_action)


__all__ = [
    "ARParentalControlAction",
    "ARParentalControlRule",
    "run_action",
]
