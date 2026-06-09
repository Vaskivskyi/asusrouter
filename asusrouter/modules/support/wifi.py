"""Supported WiFi."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.wifi import ARWiFiGeneration, ARWiFiMultiBand
from asusrouter.tools.readers import is_true_in_dict

# Translation table should be ordered
# from the highest to the lowest generation
TRANSLATION_TABLE_WIFI_GENERATION: dict[ARSupportValue, ARWiFiGeneration] = {
    ARSupportValue.WIFI_7: ARWiFiGeneration.WIFI_7,
    ARSupportValue.WIFI_6: ARWiFiGeneration.WIFI_6,
    ARSupportValue.WIFI_5: ARWiFiGeneration.WIFI_5,
}


def translate_wifi_generation(data: dict[str, Any]) -> ARWiFiGeneration:
    """Translate WiFi generation data to ARWiFiGeneration."""

    if not isinstance(data, dict):
        return ARWiFiGeneration.UNKNOWN  # type: ignore[unreachable]

    for (
        support_value,
        generation_type,
    ) in TRANSLATION_TABLE_WIFI_GENERATION.items():
        if is_true_in_dict(support_value.value, data):
            return generation_type

    return ARWiFiGeneration.UNKNOWN


def translate_wifi_multiband(data: dict[str, Any]) -> ARWiFiMultiBand:
    """Translate WiFi multiband data to ARWiFiMultiBand."""

    if not isinstance(data, dict):
        return ARWiFiMultiBand.UNKNOWN  # type: ignore[unreachable]

    if is_true_in_dict(ARSupportValue.WIFI_BANDS_QUAD.value, data):
        return ARWiFiMultiBand.QUADBAND

    if is_true_in_dict(ARSupportValue.WIFI_BANDS_TRI.value, data):
        return ARWiFiMultiBand.TRIBAND

    if is_true_in_dict(ARSupportValue.WIFI_BANDS_DUAL.value, data):
        return ARWiFiMultiBand.DUALBAND

    return ARWiFiMultiBand.UNKNOWN


def translate_wifi_units(data: dict[str, Any]) -> list[int]:
    """Translate WiFi units data to a list of unit indices."""

    if not isinstance(data, dict):
        return []  # type: ignore[unreachable]

    # Fast-path for no WiFi
    if is_true_in_dict(ARSupportValue.WIFI_UNIT_NONE.value, data):
        return []

    return [
        unit_index
        for unit_value, unit_index in (
            (ARSupportValue.WIFI_UNIT_0.value, 0),
            (ARSupportValue.WIFI_UNIT_1.value, 1),
            (ARSupportValue.WIFI_UNIT_2.value, 2),
        )
        if is_true_in_dict(unit_value, data)
    ]
