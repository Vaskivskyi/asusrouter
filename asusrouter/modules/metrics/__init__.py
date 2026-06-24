"""Metrics module for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARMetricType(FromStrMixin, StrEnum):
    """A measurable metric, reusable across modules."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    FREE = "free"
    TOTAL = "total"
    USAGE = "usage"
    USED = "used"
