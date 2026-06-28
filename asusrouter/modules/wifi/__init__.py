"""WiFi module for AsusRouter."""

from __future__ import annotations

from enum import IntEnum, StrEnum

from asusrouter.const import UNKNOWN_MEMBER, UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromIntMixin, FromStrMixin


class ARWiFiBand(FromStrMixin, StrEnum):
    """WiFi band types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    BAND_2G1 = "2g1"
    BAND_2G2 = "2g2"
    BAND_5G1 = "5g1"
    BAND_5G2 = "5g2"
    BAND_6G1 = "6g1"
    BAND_6G2 = "6g2"


class ARWiFiFrequency(FromStrMixin, StrEnum):
    """WiFi frequency types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    FREQ_2G = "2g"
    FREQ_5G = "5g"
    FREQ_6G = "6g"


class ARWiFiAuth(FromStrMixin, StrEnum):
    """WiFi authentication / security method."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    AES = "aes"
    NONE = "none"
    OPEN = "open"
    TKIP = "tkip"
    WPA2_EAP = "wpa2-eap"
    WPA2_PSK = "wpa2-psk"
    WPA3_SAE = "wpa3-sae"
    WPA_EAP = "wpa-eap"
    WPA_PSK = "wpa-psk"


class ARWiFiGeneration(FromIntMixin, IntEnum):
    """WiFi generation types."""

    UNKNOWN = UNKNOWN_MEMBER

    WIFI_5 = 5
    WIFI_6 = 6
    WIFI_7 = 7


class ARWiFiMultiBand(FromIntMixin, IntEnum):
    """WiFi multiband types."""

    UNKNOWN = UNKNOWN_MEMBER

    SINGLEBAND = 1
    DUALBAND = 2
    TRIBAND = 3
    QUADBAND = 4
