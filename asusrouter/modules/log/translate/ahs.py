"""ASUS ahs daemon log event translation for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.enum import FromStrMixin


class AREventAhs(FromStrMixin, StrEnum):
    """Ahs daemon event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    JSON_UPDATE = "json_update"
    TERMINATE = "terminate"


PATTERNS = ARLogPatternSet(
    AREventAhs.UNKNOWN,
    (
        ARLogPattern(
            AREventAhs.JSON_UPDATE,
            r"Update ahs JSON file",
            marker="Update ahs JSON file",
        ),
        ARLogPattern(
            AREventAhs.TERMINATE,
            r"Terminate ahs daemon",
            marker="Terminate ahs daemon",
        ),
    ),
)
