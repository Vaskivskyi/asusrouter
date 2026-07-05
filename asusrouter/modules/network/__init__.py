"""Network module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.network.enums import (
    ARNetworkField,
    ARNetworkSchedule,
    ARNetworkType,
)
from asusrouter.modules.network.source import (
    ARNetworkSource,
    ARNetworkSourceUniversal,
    get_state,
    translate_state,
)

__all__ = [
    "ARNetworkField",
    "ARNetworkSchedule",
    "ARNetworkSource",
    "ARNetworkSourceUniversal",
    "ARNetworkType",
    "get_state",
    "translate_state",
]
