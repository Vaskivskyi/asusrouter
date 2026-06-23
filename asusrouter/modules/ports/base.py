"""Base definitions for the ports module.

Port enums and the readers shared by the port_status and ethernet
parsers. Kept separate from the package __init__ so the parsing
submodules can import them without a circular import.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Any

from asusrouter.const import UNKNOWN_MEMBER, UNKNOWN_MEMBER_STR
from asusrouter.modules.ports.speed import ARPortSpeed
from asusrouter.modules.usb import ARUSBSpeed
from asusrouter.tools.converters_v2.int import int_to_bits
from asusrouter.tools.converters_v2.raw import raw_to_int
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

    AI = "ai"
    ETHERNET = "ethernet"
    LAN = "lan"
    MOCA = "moca"
    POWERLINE = "powerline"
    SFPP = "sfpp"
    USB = "usb"
    WAN = "wan"


class ARPortProperty(StrEnum):
    """A single property of a port."""

    NATIVE_NAME = "native_name"
    STATE = "state"
    LINK_RATE = "link_rate"
    MAX_RATE = "max_rate"
    ROLE = "role"
    CAPABILITIES = "capabilities"
    EXTENDED = "extended"
    IFNAME = "ifname"
    UI_DISPLAY = "ui_display"
    SEQ_NO = "seq_no"
    FLAG = "flag"
    PHY_PORT_ID = "phy_port_id"
    EXT_PORT_ID = "ext_port_id"
    TIMEOUT = "timeout"
    LINK_RECOVER = "link_recover"
    CABLE = "cable"
    DEVICES = "devices"


class ARPortsInfo(StrEnum):
    """Node-level information reported alongside the ports.

    Values match the raw keys returned by the device.
    """

    CD_GOOD_TO_GO = "cd_good_to_go"
    POWER_LIMIT = "power_limit"
    POWER_REMAIN = "power_remain"
    PER_PORT_POWER_LIMIT = "per_port_power_limit"


class ARPortCablePair(StrEnum):
    """The four twisted pairs of an ethernet cable.

    Values match the raw keys returned by the device.
    """

    BROWN = "brown"
    BLUE = "blue"
    GREEN = "green"
    ORANGE = "orange"


@dataclass(frozen=True)
class ARPortCableState:
    """Diagnostic state of a single ethernet cable pair."""

    status: int
    length: int


@dataclass(frozen=True)
class ARPortsData:
    """Ports and node-level info reported by a single device.

    Each entry in `ports` is a property mapping that always carries
    `ARPortProperty.NATIVE_NAME`.
    """

    info: dict[ARPortsInfo, Any]
    ports: list[dict[ARPortProperty, Any]]


_CAPABILITIES: list[ARPortCapability] = [
    cap for cap in ARPortCapability if cap.value >= 0
]

# The order is important: first matching capability wins
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
) -> ARPortSpeed | ARUSBSpeed:
    """Read port link rate for the given port type."""

    if port_type == ARPortType.USB:
        return ARUSBSpeed.from_value(raw)
    return ARPortSpeed.from_value(raw)


def read_port_capabilities(raw: Any) -> dict[ARPortCapability, bool]:
    """Read port capabilities from raw integer."""

    value = raw_to_int(raw)
    if not isinstance(value, int) or value < 0:
        return {}
    bits = int_to_bits(value)
    return {cap: cap.value in bits for cap in _CAPABILITIES}


__all__ = [
    "ARPortCablePair",
    "ARPortCableState",
    "ARPortCapability",
    "ARPortSpeed",
    "ARPortProperty",
    "ARPortType",
    "ARPortsData",
    "ARUSBSpeed",
    "ARPortsInfo",
    "read_port_capabilities",
    "read_port_speed",
    "read_port_type",
]
