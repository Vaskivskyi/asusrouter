"""Port module for AsusRouter.

This module is for physical ports on the router, e.g. LAN, WAN, USB, etc."""

from enum import IntEnum, StrEnum


class PortSpeed(IntEnum):
    """Port speed class."""

    LINK_DOWN = 0
    LINK_10 = 10
    LINK_100 = 100
    LINK_1000 = 1000
    LINK_2500 = 2500
    LINK_5000 = 5000
    LINK_10000 = 10000

    UNKNOWN = -999


class USBSpeed(IntEnum):
    """USB speed class."""

    USB_DOWN = 0
    USB_20 = 480
    USB_30 = 5000
    USB_31 = 10000
    USB_32 = 20000

    UNKNOWN = -999


PORT_SPEED = {
    "t": PortSpeed.LINK_10,
    "X": PortSpeed.LINK_DOWN,
    "M": PortSpeed.LINK_100,
    "G": PortSpeed.LINK_1000,
    "Q": PortSpeed.LINK_2500,
    "F": PortSpeed.LINK_5000,
    "T": PortSpeed.LINK_10000,
}

PORT_SUBTYPE = {
    1: PORT_SPEED["M"],
    2: PORT_SPEED["M"],
    3: PORT_SPEED["G"],
    4: PORT_SPEED["F"],
    5: PORT_SPEED["Q"],
    6: PORT_SPEED["T"],
    7: PORT_SPEED["T"],
}


class PortType(StrEnum):
    """Port type class."""

    ETHERNET = "ethernet"
    LAN = "lan"
    MOCA = "moca"
    POWERLINE = "powerline"
    SFPP = "sfpp"
    USB = "usb"
    WAN = "wan"

    UNKNOWN = "unknown"


class PortCapability(IntEnum):
    """Port capability class."""

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


# Map to convert port capabilities to port types
# The order is important!
PORT_CAP2TYPE = {
    PortCapability.WAN: PortType.WAN,
    PortCapability.LAN: PortType.LAN,
    PortCapability.USB: PortType.USB,
    PortCapability.MOCA: PortType.MOCA,
}

PORT_TYPE2LINK = {
    PortType.LAN: PortSpeed,
    PortType.MOCA: PortSpeed,
    PortType.USB: USBSpeed,
    PortType.WAN: PortSpeed,
}
