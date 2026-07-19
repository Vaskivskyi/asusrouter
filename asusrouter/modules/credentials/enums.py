"""Credentials enums for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARCredentialsStatus(FromStrMixin, StrEnum):
    """chpass.cgi outcome. Values are the device `statusCode` strings."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    LOCKED_OUT = "402"  # five failed attempts, login temporarily blocked
    SUCCESS = "200"
    WRONG_PASSWORD = "401"


__all__ = [
    "ARCredentialsStatus",
]
