"""Common connection module for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARConnectionType(FromStrMixin, StrEnum):
    """How a device is connected."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    WIRED = "wired"
    WIRELESS = "wireless"
