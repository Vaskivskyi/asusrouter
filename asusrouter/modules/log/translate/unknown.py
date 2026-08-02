"""Fallback log event type for AsusRouter (unmapped programs)."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class AREventUnknown(FromStrMixin, StrEnum):
    """Fallback event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR
