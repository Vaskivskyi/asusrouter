"""Traffic enums for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARTrafficType(FromStrMixin, StrEnum):
    """A traffic link / interface type."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    BACKHAUL = "backhaul"
    BRIDGE = "bridge"
    LACP = "lacp"
    LACP1 = "lacp1"
    LACP2 = "lacp2"
    USB = "usb"
    WAN = "wan"
    WIRED = "wired"


__all__ = [
    "ARTrafficType",
]
