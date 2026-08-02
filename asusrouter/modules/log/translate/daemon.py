"""Daemon lifecycle log event translation for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.enum import FromStrMixin


class AREventDaemon(FromStrMixin, StrEnum):
    """Daemon lifecycle event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    STARTED = "started"
    STOPPED = "stopped"


# Shared by every daemon reporting only that it came up or went down
PATTERNS = ARLogPatternSet(
    AREventDaemon.UNKNOWN,
    (
        # Matching the verb stem covers the firmware's own `stoped`
        ARLogPattern(
            {
                "start": AREventDaemon.STARTED,
                "stop": AREventDaemon.STOPPED,
            },
            r"daemon is (?P<event_type>start|stop)",
            marker="daemon is",
        ),
    ),
)
