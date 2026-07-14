"""LED enums for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARLedField(FromStrMixin, StrEnum):
    """Keys of the LED data dict."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    STATE = "state"


__all__ = [
    "ARLedField",
]
