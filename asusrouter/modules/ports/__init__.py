"""Ports module for AsusRouter.

This module is for physical ports on the router, e.g. LAN, WAN, USB, etc.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Any

from asusrouter.const import UNKNOWN_MEMBER, UNKNOWN_MEMBER_STR
from asusrouter.modules.ports.ethernet import (
    ARPortEthernetSpeed,
    read_ethernet_port_speed,
)
from asusrouter.modules.ports.usb import ARPortUSBSpeed
from asusrouter.tools.converters import safe_int
from asusrouter.tools.converters_v2.int import int_to_bits
from asusrouter.tools.enum import FromIntMixin, FromStrMixin


class ARPortCapability(FromIntMixin, IntEnum):
    """Port capability."""

    UNKNOWN = UNKNOWN_MEMBER

    WAN = 0
    LAN = 1
    GAME = 2
    PLC = 3
    WAN2 = 4
    WAN3 = 5
    SFPP = 6
    USB = 7
    MOBILE = 8
    WANLAN = 9
    MOCA = 10
    IPTV_BRIDGE = 26
    IPTV_VOIP = 27
    IPTV_STB = 28
    DUALWAN_SECONDARY = 29
    DUALWAN_PRIMARY = 30


class ARPortType(FromStrMixin, StrEnum):
    """Port type."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    ETHERNET = "ethernet"
    LAN = "lan"
    MOCA = "moca"
    POWERLINE = "powerline"
    SFPP = "sfpp"
    USB = "usb"
    WAN = "wan"


_CAPABILITIES: list[ARPortCapability] = [
    cap for cap in ARPortCapability if cap.value >= 0
]

# The order is important: first matching capability wins.
_PORT_CAPABILITY_TO_TYPE: dict[ARPortCapability, ARPortType] = {
    ARPortCapability.WAN: ARPortType.WAN,
    ARPortCapability.LAN: ARPortType.LAN,
    ARPortCapability.USB: ARPortType.USB,
    ARPortCapability.MOCA: ARPortType.MOCA,
}


def read_port_type(capabilities: dict[ARPortCapability, bool]) -> ARPortType:
    """Read port type from capability bits."""

    return next(
        (
            port_type
            for cap, port_type in _PORT_CAPABILITY_TO_TYPE.items()
            if capabilities.get(cap) is True
        ),
        ARPortType.UNKNOWN,
    )


def read_port_speed(
    port_type: ARPortType,
    raw: int,
) -> ARPortEthernetSpeed | ARPortUSBSpeed:
    """Read port link rate for the given port type."""

    if port_type == ARPortType.USB:
        return ARPortUSBSpeed.from_value(raw)
    return ARPortEthernetSpeed.from_value(raw)


def read_port_capabilities(raw: Any) -> dict[ARPortCapability, bool]:
    """Read port capabilities from raw integer."""

    value = safe_int(raw)
    if not isinstance(value, int) or value < 0:
        return {}
    bits = int_to_bits(value)
    return {cap: cap.value in bits for cap in _CAPABILITIES}


__all__ = [
    "ARPortCapability",
    "ARPortEthernetSpeed",
    "ARPortType",
    "ARPortUSBSpeed",
    "read_ethernet_port_speed",
    "read_port_capabilities",
    "read_port_speed",
    "read_port_type",
]
