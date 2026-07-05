"""Network enums for AsusRouter."""

from __future__ import annotations

from enum import IntEnum, StrEnum

from asusrouter.const import UNKNOWN_MEMBER, UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromIntMixin, FromStrMixin


class ARNetworkField(FromStrMixin, StrEnum):
    """Keys of a network profile dict."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    # Network
    AP_ISOLATE = "ap_isolate"
    BANDS = "bands"
    BANDWIDTH_LIMIT_DOWNLOAD = "bandwidth_limit_download"
    BANDWIDTH_LIMIT_UPLOAD = "bandwidth_limit_upload"
    ENABLED = "enabled"
    EXPIRE = "expire"  # legacy guest time-limit duration in seconds
    EXPIRE_REMAINING = "expire_remaining"  # legacy guest seconds left
    EXPIRY = "expiry"  # SDN one-time schedule `start,end` timestamps
    HIDDEN = "hidden"
    LAN_ACCESS = "lan_access"
    MAC_FILTER_LIST = "mac_filter_list"
    MAC_FILTER_MODE = "mac_filter_mode"
    MLO = "mlo"
    SCHEDULE = "schedule"
    SCHEDULE_MODE = "schedule_mode"
    SECURITY = "security"
    SSID = "ssid"
    WIFI7 = "wifi7"

    # Security (per-band, nested under SECURITY)
    AUTH = "auth"
    CIPHER = "cipher"
    PASSWORD = "password"


class ARNetworkSchedule(FromIntMixin, IntEnum):
    """Network WiFi scheduling mode (`timesched`)."""

    UNKNOWN = UNKNOWN_MEMBER

    DISABLED = 0
    SCHEDULED = 1
    ONE_TIME = 2


class ARNetworkType(FromStrMixin, StrEnum):
    """Network profile type, from the SDN profile name (`sdn_rl`)."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    CUSTOMIZED = "Customized"
    DEFAULT = "DEFAULT"
    GUEST = "guest"
    LEGACY = "LEGACY"
    MAINBH = "MAINBH"
    MAINFH = "MAINFH"
    MLO = "MLO"
