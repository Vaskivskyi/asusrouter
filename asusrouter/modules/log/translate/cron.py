"""Cron (crond) log event translation for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.enum import FromStrMixin


class AREventCron(FromStrMixin, StrEnum):
    """Cron event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    TIME_DISPARITY = "time_disparity"


PATTERNS = ARLogPatternSet(
    AREventCron.UNKNOWN,
    (
        # Minutes the clock jumped away from the base
        ARLogPattern(
            AREventCron.TIME_DISPARITY,
            r"time disparity of (?P<minutes>-?\d+) minutes detected",
            convert={AREventKey.MINUTES: int},
            marker="time disparity",
        ),
    ),
)
