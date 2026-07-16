"""Supported WiFi."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_enum_translator
from asusrouter.modules.wifi import ARWiFiGeneration, ARWiFiMultiBand
from asusrouter.tools.readers_v2 import is_true_in_dict

# First match wins
translate_wifi_generation = make_enum_translator(
    {
        ARSupportValue.WIFI_7.value: ARWiFiGeneration.WIFI_7,
        ARSupportValue.WIFI_6.value: ARWiFiGeneration.WIFI_6,
        ARSupportValue.WIFI_5.value: ARWiFiGeneration.WIFI_5,
    },
    ARWiFiGeneration.UNKNOWN,
)
# First match wins
translate_wifi_multiband = make_enum_translator(
    {
        ARSupportValue.WIFI_BANDS_QUAD.value: ARWiFiMultiBand.QUADBAND,
        ARSupportValue.WIFI_BANDS_TRI.value: ARWiFiMultiBand.TRIBAND,
        ARSupportValue.WIFI_BANDS_DUAL.value: ARWiFiMultiBand.DUALBAND,
    },
    ARWiFiMultiBand.UNKNOWN,
)


def translate_wifi_units(data: dict[str, Any]) -> list[int]:
    """Translate WiFi units data to a list of unit indices."""

    if not isinstance(data, dict):
        return []  # type: ignore[unreachable]

    # Fast-path for no WiFi
    if is_true_in_dict(ARSupportValue.WIFI_UNIT_NONE.value, data):
        return []

    return [
        unit_index
        for unit_value, unit_index in {
            ARSupportValue.WIFI_UNIT_0.value: 0,
            ARSupportValue.WIFI_UNIT_1.value: 1,
            ARSupportValue.WIFI_UNIT_2.value: 2,
        }.items()
        if is_true_in_dict(unit_value, data)
    ]
