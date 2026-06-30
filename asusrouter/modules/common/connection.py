"""Common connection module for AsusRouter."""

from __future__ import annotations

from enum import IntEnum, StrEnum

from asusrouter.const import UNKNOWN_MEMBER, UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromIntMixin, FromStrMixin


class ARConnectionMethod(FromStrMixin, StrEnum):
    """How a connection is established."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    DHCP = "dhcp"
    L2TP = "l2tp"
    PPPOE = "pppoe"
    PPTP = "pptp"
    STATIC = "static"


class ARConnectionStatus(FromIntMixin, IntEnum):
    """Connection status as reported by the router."""

    UNKNOWN = UNKNOWN_MEMBER

    ERROR = -1
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2


class ARConnectionType(FromStrMixin, StrEnum):
    """How a device is connected."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    WIRED = "wired"
    WIRELESS = "wireless"
