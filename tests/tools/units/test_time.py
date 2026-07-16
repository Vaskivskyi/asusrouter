"""Tests for the time unit converter."""

from __future__ import annotations

import pytest

from asusrouter.tools.units.time import TimeUnitConverter, UnitOfTime


@pytest.mark.parametrize(
    ("value", "from_unit", "to_unit", "expected"),
    [
        (1000.0, UnitOfTime.MILLISECOND, UnitOfTime.SECOND, 1.0),
        (1e6, UnitOfTime.MICROSECOND, UnitOfTime.SECOND, 1.0),
        (1e9, UnitOfTime.NANOSECOND, UnitOfTime.SECOND, 1.0),
        (2.0, UnitOfTime.MINUTE, UnitOfTime.SECOND, 120.0),
        (1.0, UnitOfTime.HOUR, UnitOfTime.MINUTE, 60.0),
        (1.0, UnitOfTime.DAY, UnitOfTime.HOUR, 24.0),
        (1.0, UnitOfTime.WEEK, UnitOfTime.DAY, 7.0),
    ],
)
def test_time_unit_converter(
    value: float,
    from_unit: UnitOfTime,
    to_unit: UnitOfTime,
    expected: float,
) -> None:
    """Time conversions produce the expected value."""

    TimeUnitConverter.get_unit_ratio.cache_clear()
    result = TimeUnitConverter.convert(value, from_unit, to_unit)
    assert result == pytest.approx(expected)


def test_time_unit_convert_to_base() -> None:
    """convert_to_base returns the value in seconds."""

    result = TimeUnitConverter.convert_to_base(500.0, UnitOfTime.MILLISECOND)
    assert result == pytest.approx(0.5)
