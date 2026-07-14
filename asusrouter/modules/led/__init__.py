"""LED module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.led.action import ARLedAction, run_action
from asusrouter.modules.led.enums import ARLedField
from asusrouter.modules.led.legacy import AsusLED, keep_state, set_state
from asusrouter.modules.led.source import (
    LED_REQUEST,
    ARLedSource,
    ARLedSourceUniversal,
    get_state,
    translate_state,
)

__all__ = [
    "LED_REQUEST",
    "ARLedAction",
    "ARLedField",
    "ARLedSource",
    "ARLedSourceUniversal",
    "AsusLED",
    "get_state",
    "keep_state",
    "run_action",
    "set_state",
    "translate_state",
]
