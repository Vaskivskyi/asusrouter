"""Supported SpeedTest."""

from __future__ import annotations

from asusrouter.modules.speedtest import ARSpeedTestCapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import (
    make_bool_translator,
    make_list_translator,
)

translate_speedtest = make_bool_translator(ARSupportValue.SPEEDTEST.value)
translate_speedtest_capabilities = make_list_translator(
    {
        ARSupportValue.SPEEDTEST_10G.value: ARSpeedTestCapability.SPEED_10G,
    }
)
