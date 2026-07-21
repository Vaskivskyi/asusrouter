"""WAN enums for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARDualWanMode(FromStrMixin, StrEnum):
    """Dual WAN operating mode."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    FAILOVER = "fo"
    FALLBACK = "fb"
    LOAD_BALANCE = "lb"


class ARWANCapability(FromStrMixin, StrEnum):
    """WAN capabilities."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    AGGREGATION = "aggregation"
    DUALWAN = "dualwan"
    LIMIT = "limit"


__all__ = [
    "ARDualWanMode",
    "ARWANCapability",
]
