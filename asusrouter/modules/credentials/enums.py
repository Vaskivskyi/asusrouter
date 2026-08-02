"""Credentials enums for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARCredentialsCapability(FromStrMixin, StrEnum):
    """Login capabilities a device advertises. Acts as a database."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    CHPASS = "chpass"  # modern backend; absent on legacy firmware
    PASSWORD_MAX_LENGTH = "password_max_length"
    SECURE_DEFAULT = "secure_default"  # gates the strict complexity rules
    USERNAME_MAX_LENGTH = "username_max_length"


class ARCredentialsStatus(FromStrMixin, StrEnum):
    """CHPASS outcome. Values are the device `statusCode` strings."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    LOCKED_OUT = "402"  # five failed attempts, login temporarily blocked
    SUCCESS = "200"
    WRONG_PASSWORD = "401"


__all__ = [
    "ARCredentialsCapability",
    "ARCredentialsStatus",
]
