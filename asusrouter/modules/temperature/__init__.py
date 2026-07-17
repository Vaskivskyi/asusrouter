"""Temperature module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.temperature.enums import ARTemperatureType
from asusrouter.modules.temperature.source import (
    ARTemperatureSource,
    ARTemperatureSourceUniversal,
    fetch_state,
    translate_state,
)

__all__ = [
    "ARTemperatureSource",
    "ARTemperatureSourceUniversal",
    "ARTemperatureType",
    "fetch_state",
    "translate_state",
]
