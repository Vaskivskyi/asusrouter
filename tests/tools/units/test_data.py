"""Tests for the data unit converter."""

from __future__ import annotations

import pytest

from asusrouter.tools.units.data import DataUnitConverter, UnitOfData


@pytest.mark.parametrize(
    ("unit_from", "factor"),
    [
        (UnitOfData.BYTE, 8),
        (UnitOfData.KILOBIT, 1e3),
        (UnitOfData.MEGABIT, 1e6),
        (UnitOfData.GIGABIT, 1e9),
        (UnitOfData.TERABIT, 1e12),
        (UnitOfData.KIBIBIT, 2**10),
        (UnitOfData.MEBIBIT, 2**20),
        (UnitOfData.GIBIBIT, 2**30),
        (UnitOfData.TEBIBIT, 2**40),
        (UnitOfData.KILOBYTE, 8e3),
        (UnitOfData.MEGABYTE, 8e6),
        (UnitOfData.GIGABYTE, 8e9),
        (UnitOfData.TERABYTE, 8e12),
        (UnitOfData.KIBIBYTE, 2**13),
        (UnitOfData.MEBIBYTE, 2**23),
        (UnitOfData.GIBIBYTE, 2**33),
        (UnitOfData.TEBIBYTE, 2**43),
    ],
)
def test_data_unit_factors(unit_from: UnitOfData, factor: float) -> None:
    """Test known conversion factors to bits."""

    assert DataUnitConverter.convert(1.0, unit_from, UnitOfData.BIT) == factor
    assert DataUnitConverter.convert_to_base(1.0, unit_from) == factor
