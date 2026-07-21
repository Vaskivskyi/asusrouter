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
_generation = make_enum_translator(
    {
        ARSupportValue.WIFI_7.value: ARWiFiGeneration.WIFI_7,
        ARSupportValue.WIFI_6.value: ARWiFiGeneration.WIFI_6,
        ARSupportValue.WIFI_5.value: ARWiFiGeneration.WIFI_5,
    },
    ARWiFiGeneration.UNKNOWN,
)
# First match wins
_multiband = make_enum_translator(
    {
        ARSupportValue.WIFI_BANDS_QUAD.value: ARWiFiMultiBand.QUADBAND,
        ARSupportValue.WIFI_BANDS_TRI.value: ARWiFiMultiBand.TRIBAND,
        ARSupportValue.WIFI_BANDS_DUAL.value: ARWiFiMultiBand.DUALBAND,
    },
    ARWiFiMultiBand.UNKNOWN,
)

_UNITS = {
    ARSupportValue.WIFI_UNIT_0.value: 0,
    ARSupportValue.WIFI_UNIT_1.value: 1,
    ARSupportValue.WIFI_UNIT_2.value: 2,
}

WiFiCapabilityValue = (
    bool | int | ARWiFiGeneration | ARWiFiMultiBand | list[int]
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


def _units(data: dict[str, Any]) -> list[int]:
    """Wireless unit indices; empty when the device reports no WiFi."""

    if is_true_in_dict(ARSupportValue.WIFI_UNIT_NONE.value, data):
        return []
    return [
        idx for value, idx in _UNITS.items() if is_true_in_dict(value, data)
    ]


def translate_wifi_capabilities(
    data: dict[str, Any],
) -> dict[ARWiFiCapability, WiFiCapabilityValue]:
    """Map advertised WiFi capabilities; each key present only when known."""

    capabilities: dict[ARWiFiCapability, WiFiCapabilityValue] = {
        capability: True
        for key, capability in _CAPABILITY_FLAGS.items()
        if is_true_in_dict(key, data)
    }

    generation = _generation(data)
    if generation is not ARWiFiGeneration.UNKNOWN:
        capabilities[ARWiFiCapability.GENERATION] = generation

    multiband = _multiband(data)
    if multiband is not ARWiFiMultiBand.UNKNOWN:
        capabilities[ARWiFiCapability.MULTIBAND] = multiband

    if smart_connect := _smart_connect(data):
        capabilities[ARWiFiCapability.SMART_CONNECT] = smart_connect

    if units := _units(data):
        capabilities[ARWiFiCapability.UNITS] = units

    return capabilities


def translate_wifi(data: dict[str, Any]) -> bool:
    """Whether the device has WiFi - false when it opts out or has none."""

    if is_true_in_dict(ARSupportValue.WIFI_UNIT_NONE.value, data):
        return False
    return bool(translate_wifi_capabilities(data))
