"""Supported SpeedTest."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.speedtest import ARSpeedTestCapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_bool_translator
from asusrouter.tools.readers import is_true_in_dict

translate_speedtest = make_bool_translator(ARSupportValue.SPEEDTEST.value)


def translate_speedtest_capabilities(
    data: dict[str, Any],
) -> list[ARSpeedTestCapability]:
    """Translate SpeedTest capabilities support data."""

    if not isinstance(data, dict):
        return []  # type: ignore[unreachable]

    result: list[ARSpeedTestCapability] = []

    if is_true_in_dict(ARSupportValue.SPEEDTEST_10G.value, data):
        result.append(ARSpeedTestCapability.SPEED_10G)

    return result
