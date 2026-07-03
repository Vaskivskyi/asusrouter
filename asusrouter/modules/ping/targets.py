"""Ping targets module for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from asusrouter.modules.action import ARAction, ARActionType
from asusrouter.modules.common.status import MODIFY_KEY
from asusrouter.modules.endpoint_v2 import (
    ACTION_MODE_APPLY,
    AREndpoint,
    build_push_request,
)
from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters_v2.raw import raw_to_bool
from asusrouter.tools.identifiers.ip import IpAddress
from asusrouter.tools.types import ARCallbackType

_LOGGER = logging.getLogger(__name__)


# Data model


@dataclass
class ARPingTarget:
    """A DNS ping target."""

    name: str
    ip: IpAddress


# A target, or something coercible into one
ARPingTargetInput = ARPingTarget | IpAddress | str


# Sources and actions


class ARPingTargetsSource(ARDataSource):
    """AsusRouter ping targets data source."""


# Universal instance - preferred
ARPingTargetsSourceUniversal: ARPingTargetsSource = ARPingTargetsSource()


class ARPingTargetsAction(ARAction):
    """Add, remove, or clean the DNS ping target list."""

    def __init__(
        self,
        op: ARActionType,
        targets: ARPingTargetInput | list[ARPingTargetInput] | None = None,
    ) -> None:
        """Initialize the action with an operation and optional target(s)."""

        super().__init__()

        # Accept a single target or a list; a bare str must not be iterated
        if targets is None:
            provided: list[ARPingTargetInput] = []
        elif isinstance(targets, (ARPingTarget, IpAddress, str)):
            provided = [targets]
        else:
            provided = list(targets)

        self.op = op
        self.targets: list[ARPingTarget] = [
            normalized
            for target in provided
            if (normalized := _normalize(target)) is not None
        ]


# Fetch


async def get_state(
    callback: ARCallbackType,
    source: ARPingTargetsSource,
    *,
    get_data_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> Any:
    """Fetch the raw dns_ping_list value."""

    if get_data_callback is None:
        return None

    values = await get_data_callback(ARNvramType.DNS_PING_LIST)

    if isinstance(values, dict):
        return values.get(ARNvramType.DNS_PING_LIST)
    return None


def translate_state(data: Any, **kwargs: Any) -> list[ARPingTarget]:
    """Translate the raw dns_ping_list value into targets."""

    if not isinstance(data, str):
        return []
    return _parse_targets(data)


def _parse_targets(raw: str) -> list[ARPingTarget]:
    """Parse a `<name>ip` delimited dns_ping_list value into targets."""

    # nvram list values arrive HTML-entity encoded: `<`=`&#60`, `>`=`&#62`
    decoded = raw.replace("&#60", "<").replace("&#62", ">")
    targets: list[ARPingTarget] = []
    for entry in decoded.split("<"):
        if not entry:
            continue
        name, _, ip_raw = entry.partition(">")
        ip = IpAddress.from_value_safe(ip_raw)
        if ip is not None:
            targets.append(ARPingTarget(name=name, ip=ip))
    return targets


# Action

# Default name for a target added by bare IP; names need not be unique
_DEFAULT_TARGET_NAME = "target"


def _normalize(target: ARPingTargetInput) -> ARPingTarget | None:
    """Coerce a target, IP, or IP string into a target; drop if invalid.

    The IP is always coerced to `IpAddress` - a target constructed with a
    string IP would otherwise break IP-keyed dedup and comparison.
    """

    name: str
    value: Any
    if isinstance(target, ARPingTarget):
        name, value = target.name, target.ip
    else:
        name, value = _DEFAULT_TARGET_NAME, target

    ip = IpAddress.from_value_safe(value)
    if ip is None:
        return None
    return ARPingTarget(name=name, ip=ip)


def _encode_targets(targets: list[ARPingTarget]) -> str:
    """Encode targets into a `<name>ip` delimited dns_ping_list value."""

    return "".join(f"<{target.name}>{target.ip}" for target in targets)


def _add(
    current: list[ARPingTarget], new: list[ARPingTarget]
) -> list[ARPingTarget]:
    """Merge by IP: update the name on a match, append new IPs.

    The result is unique by IP, collapsing any pre-existing duplicates.
    """

    merged: dict[IpAddress, ARPingTarget] = {}
    for target in (*current, *new):
        merged[target.ip] = target
    return list(merged.values())


def _remove(
    current: list[ARPingTarget], drop: list[ARPingTarget]
) -> list[ARPingTarget]:
    """Drop targets by IP match, ignoring the name.

    The result is unique by IP, collapsing any pre-existing duplicates.
    """

    dropped = {target.ip for target in drop}
    merged: dict[IpAddress, ARPingTarget] = {}
    for target in current:
        if target.ip not in dropped:
            merged[target.ip] = target
    return list(merged.values())


async def _async_current(
    get_data_callback: ARCallbackType,
) -> list[ARPingTarget]:
    """Fetch the current target list, bypassing the cache."""

    values = await get_data_callback(ARNvramType.DNS_PING_LIST, force=True)
    raw = (
        values.get(ARNvramType.DNS_PING_LIST)
        if isinstance(values, dict)
        else None
    )
    return _parse_targets(raw) if isinstance(raw, str) else []


async def run_action(
    callback: ARCallbackType,
    action: ARPingTargetsAction,
    *,
    get_data_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> bool:
    """Apply an add/remove/clean operation to the ping target list."""

    if action.op is ARActionType.CLEAN:
        targets: list[ARPingTarget] = []
    elif action.op in (ARActionType.ADD, ARActionType.REMOVE):
        if not action.targets:
            _LOGGER.debug("No compatible target provided; nothing to apply")
            return False
        if get_data_callback is None:
            return False
        current = await _async_current(get_data_callback)
        targets = (
            _add(current, action.targets)
            if action.op is ARActionType.ADD
            else _remove(current, action.targets)
        )
        if targets == current:
            _LOGGER.debug("Target list unchanged; nothing to apply")
            return True
    else:
        return False

    request = build_push_request(
        ACTION_MODE_APPLY,
        {ARNvramType.DNS_PING_LIST.value: _encode_targets(targets)},
    )
    data = await callback(endpoint=AREndpoint.PUSH_DATA, request=request)
    if not isinstance(data, dict):
        return False
    return raw_to_bool(data.get(MODIFY_KEY)) is True


# Registration

ARCallReg.register_module(
    ARPingTargetsSource,
    get_state=get_state,
    translate_state=translate_state,
)
ARCallReg.register_action(ARPingTargetsAction, run_action=run_action)


__all__ = [
    "ARPingTarget",
    "ARPingTargetsAction",
    "ARPingTargetsSource",
    "ARPingTargetsSourceUniversal",
    "get_state",
    "run_action",
    "translate_state",
]
