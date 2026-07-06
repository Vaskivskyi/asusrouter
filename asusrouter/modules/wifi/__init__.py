"""WiFi module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.wifi.action import ARWiFiAction, run_action
from asusrouter.modules.wifi.enums import (
    AR_WIFI_UNIT_FALLBACK,
    ARWiFiAuth,
    ARWiFiAuthMode,
    ARWiFiBand,
    ARWiFiBandwidth,
    ARWiFiField,
    ARWiFiFrequency,
    ARWiFiGeneration,
    ARWiFiMacFilterMode,
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
    "ARWiFiAction",
    "ARWiFiAuth",
    "ARWiFiAuthMode",
    "ARWiFiBand",
    "ARWiFiBandwidth",
    "ARWiFiField",
    "ARWiFiFrequency",
    "ARWiFiGeneration",
    "ARWiFiMacFilterMode",
    "ARWiFiMultiBand",
    "ARWiFiSource",
    "ARWiFiSourceUniversal",
    "get_state",
    "run_action",
    "translate_state",
]
