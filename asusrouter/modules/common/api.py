"""Common API module for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARApiClient(FromStrMixin, StrEnum):
    """A client accessing the device API (web UI or mobile app)."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    APP = "app"
    WEB = "web"


__all__ = [
    "ARApiClient",
]
