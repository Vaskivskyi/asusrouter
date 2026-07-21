"""Supported WiFi."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_enum_translator
from asusrouter.modules.wifi import (
    ARWiFiCapability,
    ARWiFiGeneration,
    ARWiFiMultiBand,
)
from asusrouter.tools.readers import is_true_in_dict

_CAPABILITY_FLAGS = {
    ARSupportValue.WIFI_MBO.value: ARWiFiCapability.MBO,
    ARSupportValue.WIFI_MLO.value: ARWiFiCapability.MLO,
    ARSupportValue.WIFI_MUMIMO.value: ARWiFiCapability.MUMIMO,
    ARSupportValue.WIFI_OFDMA.value: ARWiFiCapability.OFDMA,
    ARSupportValue.WIFI_OFDMA_DL.value: ARWiFiCapability.OFDMA_DL,
    ARSupportValue.WIFI_POWER_CONTROL.value: ARWiFiCapability.POWER_CONTROL,
}

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


def _smart_connect(data: dict[str, Any]) -> int:
    """Band steering level: 2 for v2, 1 for v1, 0 when unsupported."""

    if is_true_in_dict(ARSupportValue.WIFI_SMART_CONNECT_V2.value, data):
        return 2
    if is_true_in_dict(
        ARSupportValue.WIFI_SMART_CONNECT.value, data
    ) or is_true_in_dict(ARSupportValue.WIFI_BANDSTEERING.value, data):
        return 1
    return 0


def translate_wifi_capabilities(
    data: dict[str, Any],
) -> dict[ARWiFiCapability, bool | int]:
    """Map advertised WiFi capabilities; SMART_CONNECT carries a level."""

    capabilities: dict[ARWiFiCapability, bool | int] = {
        capability: True
        for key, capability in _CAPABILITY_FLAGS.items()
        if is_true_in_dict(key, data)
    }
    capabilities[ARWiFiCapability.SMART_CONNECT] = _smart_connect(data)
    return capabilities


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
