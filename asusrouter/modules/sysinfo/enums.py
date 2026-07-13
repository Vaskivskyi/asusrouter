"""SysInfo enums for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARMemoryType(FromStrMixin, StrEnum):
    """A sysinfo memory value (all in bytes)."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    AVAILABLE = "available"
    BUFFERS = "buffers"
    CACHE = "cache"
    FREE = "free"
    JFFS_FREE = "jffs_free"
    JFFS_TOTAL = "jffs_total"
    JFFS_USED = "jffs_used"
    NVRAM = "nvram"
    SWAP_TOTAL = "swap_total"
    SWAP_USED = "swap_used"
    TOTAL = "total"
    USED = "used"


class ARSysInfoType(FromStrMixin, StrEnum):
    """A sysinfo data category."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    CONNECTIONS = "connections"
    LOAD_AVERAGE = "load_average"
    MEMORY = "memory"
    WLAN = "wlan"


class ARWlanClientCount(FromStrMixin, StrEnum):
    """A per-band wireless client count."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    ASSOCIATED = "associated"
    AUTHENTICATED = "authenticated"
    AUTHORIZED = "authorized"


__all__ = [
    "ARMemoryType",
    "ARSysInfoType",
    "ARWlanClientCount",
]
