"""Kernel module loader (modprobe) log event translation."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.enum import FromStrMixin


class AREventModprobe(FromStrMixin, StrEnum):
    """Kernel module loader event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    MODULE_NOT_FOUND = "module_not_found"


PATTERNS = ARLogPatternSet(
    AREventModprobe.UNKNOWN,
    (
        # A module the build leaves out, asked for at boot
        ARLogPattern(
            AREventModprobe.MODULE_NOT_FOUND,
            r"module (?P<module>\S+) not found in modules\.dep",
            marker="not found in modules.dep",
        ),
    ),
)
