"""Clock enums for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARClockField(FromStrMixin, StrEnum):
    """Keys of the clock data dict."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    BOOTTIME = "boottime"
    # The device's own clock as it read at the moment it replied
    DEVICE_TIME = "device_time"
    # Seconds since boot
    UPTIME = "uptime"


__all__ = [
    "ARClockField",
]
