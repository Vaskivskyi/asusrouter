"""Syslog daemon log event translation for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.enum import FromStrMixin


class AREventSyslog(FromStrMixin, StrEnum):
    """Syslog daemon event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    STARTED = "started"


PATTERNS = ARLogPatternSet(
    AREventSyslog.UNKNOWN,
    (
        ARLogPattern(
            AREventSyslog.STARTED,
            r"syslogd started: BusyBox v(?P<version>[\d.]+)",
            marker="syslogd started",
        ),
    ),
)
