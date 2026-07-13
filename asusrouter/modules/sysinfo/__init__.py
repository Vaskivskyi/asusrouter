"""SysInfo module for AsusRouter (Merlin firmware only)."""

from __future__ import annotations

from asusrouter.modules.sysinfo.enums import (
    ARMemoryType,
    ARSysInfoType,
    ARWlanClientCount,
)
from asusrouter.modules.sysinfo.source import (
    ARSysInfoSource,
    ARSysInfoSourceUniversal,
    get_state,
    translate_state,
)

__all__ = [
    "ARMemoryType",
    "ARSysInfoSource",
    "ARSysInfoSourceUniversal",
    "ARSysInfoType",
    "ARWlanClientCount",
    "get_state",
    "translate_state",
]
