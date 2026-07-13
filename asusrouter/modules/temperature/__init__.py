"""Temperature module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.temperature.enums import ARTemperatureType
from asusrouter.modules.temperature.source import (
    ARTemperatureSource,
    ARTemperatureSourceUniversal,
    get_state,
    translate_state,
)

__all__ = [
    "ARTemperatureSource",
    "ARTemperatureSourceUniversal",
    "ARTemperatureType",
    "get_state",
    "translate_state",
]
