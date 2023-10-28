"""Port module for AsusRouter.

This module is for physical ports on the router, e.g. LAN, WAN, USB, etc."""

from enum import Enum

from asusrouter.tools.converters import safe_bool, safe_int


class PortSpeed(int, Enum):
    """Port speed class."""

    LINK_DOWN = 0
    LINK_100 = 100
    LINK_1000 = 1000
    LINK_2500 = 2500
    LINK_10000 = 10000


PORT_SPEED = {
    "X": PortSpeed.LINK_DOWN,
    "M": PortSpeed.LINK_100,
    "G": PortSpeed.LINK_1000,
    "Q": PortSpeed.LINK_2500,
}


class PortType(str, Enum):
    """Port type class."""

    LAN = "lan"
    USB = "usb"
    WAN = "wan"


PORT_TYPE = {
    "L": PortType.LAN,
    "U": PortType.USB,
    "W": PortType.WAN,
}

PORT_VALUE_MAP = [
    ("is_on", "state", safe_bool),
    ("max_rate", "max_rate", safe_int),
    ("link_rate", "link_rate", safe_int),
]
