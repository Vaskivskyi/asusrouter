"""NTP (ntp) log event translation for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.enum import FromStrMixin


class AREventNtp(FromStrMixin, StrEnum):
    """NTP event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    START_UPDATE = "start_update"


PATTERNS = ARLogPatternSet(
    AREventNtp.UNKNOWN,
    (
        ARLogPattern(
            AREventNtp.START_UPDATE,
            r"start NTP update",
            marker="start NTP update",
        ),
    ),
)
