"""Port speed definitions for AsusRouter."""

from __future__ import annotations

from enum import IntEnum

from asusrouter.const import UNKNOWN_MEMBER
from asusrouter.tools.enum import FromIntMixin


class ARPortSpeed(FromIntMixin, IntEnum):
    """Port link speed in Mbps."""

    UNKNOWN = UNKNOWN_MEMBER

    DOWN = 0
    MBPS_10 = 10
    MBPS_100 = 100
    MBPS_1000 = 1000
    MBPS_2500 = 2500
    MBPS_5000 = 5000
    MBPS_10000 = 10000
