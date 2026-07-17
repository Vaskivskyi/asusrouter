"""Interface traffic module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.traffic.interface.source import (
    ARTrafficInterfaceSource,
    fetch_state,
    translate_state,
)

__all__ = [
    "ARTrafficInterfaceSource",
    "fetch_state",
    "translate_state",
]
