"""Ping targets data source for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from asusrouter.modules.nvram import ARNvramType, async_get_value
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.identifiers.ip import IpAddress
from asusrouter.tools.readers_v2.nvram_list import split_rows
from asusrouter.tools.types import ARCallbackType

# Data model


@dataclass
class ARPingTarget:
    """A DNS ping target."""

    name: str
    ip: IpAddress


# A target, or something coercible into one
ARPingTargetInput = ARPingTarget | IpAddress | str


# Source


class ARPingTargetsSource(ARDataSource):
    """AsusRouter ping targets data source."""


# Universal instance - preferred
ARPingTargetsSourceUniversal: ARPingTargetsSource = ARPingTargetsSource()


async def get_state(
    callback: ARCallbackType,
    source: ARPingTargetsSource,
    *,
    get_data_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> Any:
    """Fetch the raw dns_ping_list value."""

    value = await async_get_value(get_data_callback, ARNvramType.DNS_PING_LIST)
    return value if value is not None else {}


def translate_state(data: Any, **kwargs: Any) -> list[ARPingTarget]:
    """Translate the raw dns_ping_list value into targets."""

    if not isinstance(data, str):
        return []
    return _parse_targets(data)


def _parse_targets(raw: str) -> list[ARPingTarget]:
    """Parse a `<name>ip` delimited dns_ping_list value into targets."""

    targets: list[ARPingTarget] = []
    for entry in split_rows(raw):
        if not entry:
            continue
        name, _, ip_raw = entry.partition(">")
        ip = IpAddress.from_value_safe(ip_raw)
        if ip is not None:
            targets.append(ARPingTarget(name=name, ip=ip))
    return targets


# Registration

ARCallReg.register_module(
    ARPingTargetsSource,
    get_state=get_state,
    translate_state=translate_state,
)


__all__ = [
    "ARPingTarget",
    "ARPingTargetInput",
    "ARPingTargetsSource",
    "ARPingTargetsSourceUniversal",
    "get_state",
    "translate_state",
]
