"""Disk monitor (disk_monitor) log event translation for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.enum import FromStrMixin


class AREventDiskMonitor(FromStrMixin, StrEnum):
    """Disk monitor event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    FINISH = "finish"
    SIGALRM = "sigalrm"


PATTERNS = ARLogPatternSet(
    AREventDiskMonitor.UNKNOWN,
    (
        ARLogPattern(AREventDiskMonitor.FINISH, r"^Finish$", marker="Finish"),
        # The scan timer fired
        ARLogPattern(
            AREventDiskMonitor.SIGALRM, r"Got SIGALRM", marker="Got SIGALRM"
        ),
    ),
)
