"""Interface traffic module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.traffic.interface.source import (
    ARTrafficInterfaceSource,
    get_state,
    translate_state,
)

__all__ = [
    "ARTrafficInterfaceSource",
    "get_state",
    "translate_state",
]
