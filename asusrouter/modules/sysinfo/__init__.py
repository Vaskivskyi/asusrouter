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
    fetch_state,
    translate_state,
)

__all__ = [
    "ARMemoryType",
    "ARSysInfoSource",
    "ARSysInfoSourceUniversal",
    "ARSysInfoType",
    "ARWlanClientCount",
    "fetch_state",
    "translate_state",
]
