"""Tests for the data rate unit converter."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from asusrouter.tools.units.base import is_non_negative
from asusrouter.tools.units.data_rate import (
    DataRateUnitConverter,
    UnitOfDataRate,
    read_data_rate,
)


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
