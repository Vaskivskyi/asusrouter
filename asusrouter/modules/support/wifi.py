"""Supported WiFi."""

from __future__ import annotations

from enum import IntEnum
from typing import Any

from asusrouter.const import UNKNOWN_MEMBER
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.tools.enum import FromIntMixin
from asusrouter.tools.readers import is_true_in_dict


class ARSupportWiFiGeneration(FromIntMixin, IntEnum):
    """WiFi generation types."""

    UNKNOWN = UNKNOWN_MEMBER

    WIFI_5 = 5
    WIFI_6 = 6
    WIFI_7 = 7


# Tranalstion table should be ordered
# from the highest to the lowest generation
TRANSLATION_TABLE_WIFI_GENERATION: dict[
    ARSupportValue, ARSupportWiFiGeneration
] = {
    ARSupportValue.WIFI_7: ARSupportWiFiGeneration.WIFI_7,
    ARSupportValue.WIFI_6: ARSupportWiFiGeneration.WIFI_6,
    ARSupportValue.WIFI_5: ARSupportWiFiGeneration.WIFI_5,
}


def translate_wifi_generation(data: dict[str, Any]) -> ARSupportWiFiGeneration:
    """Translate WiFi generation data to ARSupportWiFiGeneration."""

    if not isinstance(data, dict):
        return ARSupportWiFiGeneration.UNKNOWN  # type: ignore[unreachable]

    for (
        support_value,
        generation_type,
    ) in TRANSLATION_TABLE_WIFI_GENERATION.items():
        if is_true_in_dict(support_value.value, data):
            return generation_type

    return ARSupportWiFiGeneration.UNKNOWN


class ARSupportWiFiMultiBand(FromIntMixin, IntEnum):
    """WiFi multiband types."""

    UNKNOWN = UNKNOWN_MEMBER

    DUALBAND = 2
    TRIBAND = 3
    QUADBAND = 4


def translate_wifi_multiband(data: dict[str, Any]) -> ARSupportWiFiMultiBand:
    """Translate WiFi multiband data to ARSupportWiFiMultiBand."""

    if not isinstance(data, dict):
        return ARSupportWiFiMultiBand.UNKNOWN  # type: ignore[unreachable]

    if is_true_in_dict(ARSupportValue.WIFI_BANDS_QUAD.value, data):
        return ARSupportWiFiMultiBand.QUADBAND

    if is_true_in_dict(ARSupportValue.WIFI_BANDS_TRI.value, data):
        return ARSupportWiFiMultiBand.TRIBAND

    if is_true_in_dict(ARSupportValue.WIFI_BANDS_DUAL.value, data):
        return ARSupportWiFiMultiBand.DUALBAND

    return ARSupportWiFiMultiBand.UNKNOWN


def translate_wifi_units(data: dict[str, Any]) -> list[int]:
    """Translate WiFi units data to a list of unit indices."""

    if not isinstance(data, dict):
        return []  # type: ignore[unreachable]

    # Short-pass for no WiFi
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
