"""LAN module for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARLANCapability(FromStrMixin, StrEnum):
    """LAN capabilities."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    AGGREGATION = "aggregation"
