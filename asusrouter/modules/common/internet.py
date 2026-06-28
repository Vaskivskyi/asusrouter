"""Common internet module for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARInternetMode(FromStrMixin, StrEnum):
    """Internet access mode for a client (parental control)."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    ALLOW = "allow"
    BLOCK = "block"
    TIME = "time"
