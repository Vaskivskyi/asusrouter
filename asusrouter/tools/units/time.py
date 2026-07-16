"""Time units for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.tools.units.base import UnitConverterBase


class UnitOfTime(StrEnum):
    """Units of time."""

    # Base unit
    SECOND = "s"

    NANOSECOND = "ns"
    MICROSECOND = "us"
    MILLISECOND = "ms"
    MINUTE = "min"
    HOUR = "h"
    DAY = "d"
    WEEK = "w"


class TimeUnitConverter(UnitConverterBase):
    """Time Unit Converter."""

    UNIT_CLASS = "time"

    _UNIT_RATIO = {
        UnitOfTime.SECOND: 1,
        UnitOfTime.NANOSECOND: 1e-9,
        UnitOfTime.MICROSECOND: 1e-6,
        UnitOfTime.MILLISECOND: 1e-3,
        UnitOfTime.MINUTE: 60,
        UnitOfTime.HOUR: 3600,
        UnitOfTime.DAY: 86400,
        UnitOfTime.WEEK: 604800,
    }
