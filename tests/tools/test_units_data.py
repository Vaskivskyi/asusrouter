"""Tests for the unit tools / data units."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from asusrouter.tools.units import (
    DataRateUnitConverter,
    DataUnitConverter,
    UnitOfData,
    UnitOfDataRate,
    is_non_negative,
    read_data_rate,
)


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


@pytest.mark.parametrize(
    ("unit_from", "factor"),
    [
        (UnitOfDataRate.BYTE_PER_SECOND, 8),
        (UnitOfDataRate.KILOBIT_PER_SECOND, 1e3),
        (UnitOfDataRate.MEGABIT_PER_SECOND, 1e6),
        (UnitOfDataRate.GIGABIT_PER_SECOND, 1e9),
        (UnitOfDataRate.TERABIT_PER_SECOND, 1e12),
        (UnitOfDataRate.KIBIBIT_PER_SECOND, 2**10),
        (UnitOfDataRate.MEBIBIT_PER_SECOND, 2**20),
        (UnitOfDataRate.GIBIBIT_PER_SECOND, 2**30),
        (UnitOfDataRate.TEBIBIT_PER_SECOND, 2**40),
        (UnitOfDataRate.KILOBYTE_PER_SECOND, 8e3),
        (UnitOfDataRate.MEGABYTE_PER_SECOND, 8e6),
        (UnitOfDataRate.GIGABYTE_PER_SECOND, 8e9),
        (UnitOfDataRate.TERABYTE_PER_SECOND, 8e12),
        (UnitOfDataRate.KIBIBYTE_PER_SECOND, 2**13),
        (UnitOfDataRate.MEBIBYTE_PER_SECOND, 2**23),
        (UnitOfDataRate.GIBIBYTE_PER_SECOND, 2**33),
        (UnitOfDataRate.TEBIBYTE_PER_SECOND, 2**43),
    ],
)
def test_data_rate_unit_factors(
    unit_from: UnitOfDataRate, factor: float
) -> None:
    """Test known conversion factors to bits per second."""

    assert (
        DataRateUnitConverter.convert(
            1.0, unit_from, UnitOfDataRate.BIT_PER_SECOND
        )
        == factor
    )
    assert DataRateUnitConverter.convert_to_base(1.0, unit_from) == factor


def test_read_data_rate() -> None:
    """read_data_rate wires the data-rate converter into read_as_base."""

    input_value = 42.0

    def return_function(x: Any) -> Any:
        """Return the input value."""

        return x

    with patch(
        "asusrouter.tools.units.data_rate.read_as_base",
        return_value=return_function,
    ) as mock_read_as_base:
        result = read_data_rate(UnitOfDataRate.MEBIBIT_PER_SECOND)

        assert input_value == result(input_value)
        mock_read_as_base.assert_called_once_with(
            DataRateUnitConverter,
            UnitOfDataRate.MEBIBIT_PER_SECOND,
            is_non_negative,
            0.0,
        )
