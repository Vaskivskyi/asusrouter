"""Common connection module for AsusRouter."""

from __future__ import annotations

from enum import IntEnum, StrEnum

from asusrouter.const import UNKNOWN_MEMBER, UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromIntMixin, FromStrMixin


class ARConnectionMethod(FromStrMixin, StrEnum):
    """How a connection is established."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    DHCP = "dhcp"
    DSLITE = "dslite"
    L2TP = "l2tp"
    LW4O6 = "lw4o6"
    MAP_E = "map-e"
    OCNVC = "ocnvc"
    PPPOE = "pppoe"
    PPTP = "pptp"
    STATIC = "static"
    V6OPT = "v6opt"
    V6PLUS = "v6plus"


class ARConnectionState(FromIntMixin, IntEnum):
    """Whether a connection is up."""

    UNKNOWN = UNKNOWN_MEMBER

    DISCONNECTED = 0
    CONNECTED = 1


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
