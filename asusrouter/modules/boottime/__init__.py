"""Boottime module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.boottime.source import (
    ARBoottime,
    ARBoottimeSource,
    ARBoottimeSourceUniversal,
    fetch_state,
    read_uptime,
    stabilize,
)

__all__ = [
    "ARBoottime",
    "ARBoottimeSource",
    "ARBoottimeSourceUniversal",
    "fetch_state",
    "read_uptime",
    "stabilize",
]
