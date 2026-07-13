"""Ports enums for AsusRouter."""

from __future__ import annotations

from enum import IntEnum, StrEnum

from asusrouter.const import UNKNOWN_MEMBER, UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromIntMixin, FromStrMixin


class ARPortCablePair(FromStrMixin, StrEnum):
    """The four twisted pairs of an ethernet cable.

    Values match the raw keys returned by the device.
    """

    UNKNOWN = UNKNOWN_MEMBER_STR

    BLUE = "blue"
    BROWN = "brown"
    GREEN = "green"
    ORANGE = "orange"


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


class ARPortProperty(FromStrMixin, StrEnum):
    """A single property of a port."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    CABLE = "cable"
    CAPABILITIES = "capabilities"
    DEVICES = "devices"
    EXTENDED = "extended"
    EXT_PORT_ID = "ext_port_id"
    FLAG = "flag"
    IFNAME = "ifname"
    LINK_RATE = "link_rate"
    LINK_RECOVER = "link_recover"
    MAX_RATE = "max_rate"
    NATIVE_NAME = "native_name"
    PHY_PORT_ID = "phy_port_id"
    ROLE = "role"
    SEQ_NO = "seq_no"
    STATE = "state"
    TIMEOUT = "timeout"
    UI_DISPLAY = "ui_display"


class ARPortSpeed(FromIntMixin, IntEnum):
    """Port link speed in Mbps."""

    UNKNOWN = UNKNOWN_MEMBER

    DOWN = 0
    MBPS_10 = 10
    MBPS_100 = 100
    MBPS_1000 = 1000
    MBPS_2500 = 2500
    MBPS_5000 = 5000
    MBPS_10000 = 10000


class ARPortsInfo(FromStrMixin, StrEnum):
    """Node-level information reported alongside the ports.

    Values match the raw keys returned by the device.
    """

    UNKNOWN = UNKNOWN_MEMBER_STR

    CD_GOOD_TO_GO = "cd_good_to_go"
    PER_PORT_POWER_LIMIT = "per_port_power_limit"
    POWER_LIMIT = "power_limit"
    POWER_REMAIN = "power_remain"


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


__all__ = [
    "ARPortCablePair",
    "ARPortCapability",
    "ARPortProperty",
    "ARPortSpeed",
    "ARPortType",
    "ARPortsInfo",
]
