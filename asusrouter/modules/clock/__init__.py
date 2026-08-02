"""Clock module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.clock.enums import ARClockField
from asusrouter.modules.clock.source import (
    ARBoottime,
    ARClockSource,
    ARClockSourceUniversal,
    fetch_state,
    read_uptime,
    stabilize,
)

__all__ = [
    "ARBoottime",
    "ARClockField",
    "ARClockSource",
    "ARClockSourceUniversal",
    "fetch_state",
    "read_uptime",
    "stabilize",
]
