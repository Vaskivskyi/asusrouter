"""SpeedTest module for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARSpeedTestCapability(FromStrMixin, StrEnum):
    """SpeedTest capabilities."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    SPEED_10G = "speed_10g"
