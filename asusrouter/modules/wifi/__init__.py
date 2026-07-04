"""WiFi module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.wifi.enums import (
    AR_WIFI_UNIT_FALLBACK,
    ARWiFiAuth,
    ARWiFiBand,
    ARWiFiBandwidth,
    ARWiFiField,
    ARWiFiFrequency,
    ARWiFiGeneration,
    ARWiFiMultiBand,
)
from asusrouter.modules.wifi.source import (
    ARWiFiSource,
    ARWiFiSourceUniversal,
    get_state,
    translate_state,
)

__all__ = [
    "AR_WIFI_UNIT_FALLBACK",
    "ARWiFiAuth",
    "ARWiFiBand",
    "ARWiFiBandwidth",
    "ARWiFiField",
    "ARWiFiFrequency",
    "ARWiFiGeneration",
    "ARWiFiMultiBand",
    "ARWiFiSource",
    "ARWiFiSourceUniversal",
    "get_state",
    "translate_state",
]
