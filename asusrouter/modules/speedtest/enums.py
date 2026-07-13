"""SpeedTest enums for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARSpeedTestCapability(FromStrMixin, StrEnum):
    """SpeedTest capabilities."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    SPEED_10G = "speed_10g"


class ARSpeedTestEventType(FromStrMixin, StrEnum):
    """Event type of a row in the Ookla result stream."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    DOWNLOAD = "download"
    ERROR = "error"
    LOG = "log"
    RESULT = "result"
    TEST_START = "testStart"
    UPLOAD = "upload"


class ARSpeedTestState(FromStrMixin, StrEnum):
    """SpeedTest run state reported in nvram `ookla_state`."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    IDLE = "0"
    RUNNING = "1"
    ERROR_DISCONNECTED = "2"
    ERROR_TIMEOUT = "3"
    ERROR_TERMINATED = "4"
    ERROR_UNKNOWN = "5"


__all__ = [
    "ARSpeedTestCapability",
    "ARSpeedTestEventType",
    "ARSpeedTestState",
]
