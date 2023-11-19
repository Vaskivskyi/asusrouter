"""Result of processing hook_002.content."""

from asusrouter import AsusData
from asusrouter.modules.led import AsusLED

expected_result = {AsusData.LED: {"state": AsusLED.OFF}}
