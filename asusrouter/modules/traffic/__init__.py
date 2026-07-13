"""Traffic module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.traffic.aimesh import ARTrafficAiMeshSource
from asusrouter.modules.traffic.base import ARTrafficLink, ARTrafficSource
from asusrouter.modules.traffic.enums import ARTrafficType
from asusrouter.modules.traffic.interface import ARTrafficInterfaceSource
from asusrouter.modules.traffic.source import get_state

__all__ = [
    "ARTrafficAiMeshSource",
    "ARTrafficInterfaceSource",
    "ARTrafficLink",
    "ARTrafficSource",
    "ARTrafficType",
    "get_state",
]
