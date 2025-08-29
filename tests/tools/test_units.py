"""Tests for the unit tools."""

from enum import StrEnum
from typing import Any
from unittest.mock import patch

import pytest

from asusrouter.error import AsusRouterError
from asusrouter.tools.units import UnitConverterBase


class MockUnits(StrEnum):
    """Mock units for testing."""

    BASE = "base"
    MEGABASE = "megabase"
    TERABASE = "terabase"


MOCK_UNIT_CLASS = "mock_units"

MOCK_UNIT_RATIOS: dict[StrEnum, float] = {
    MockUnits.BASE: 1,
    MockUnits.MEGABASE: 10**6,
    MockUnits.TERABASE: 10**12,
}


class TestUnitConverter(UnitConverterBase):
    """Test unit converter base."""

    UNIT_CLASS = MOCK_UNIT_CLASS
    UNIT_BASE = MockUnits.BASE
    VALUE_UNITS = set(MockUnits)
    _UNIT_RATIO = MOCK_UNIT_RATIOS

    @pytest.mark.parametrize(
        "unit",
        [
            MockUnits.BASE,
            MockUnits.MEGABASE,
            MockUnits.TERABASE,
        ],
    )
    def test_validate_unit(self, unit: MockUnits) -> None:
        """Test valid units pass validation."""

        # Should just pass
        self._validate_unit(unit)

    @pytest.mark.parametrize(
        "unit",
        [
            "not_a_unit",
            None,
            1.123,
        ],
    )
    def test_invalid_unit(self, unit: Any) -> None:
        """Test invalid units raise validation errors."""

        with pytest.raises(AsusRouterError, match="Unknown unit"):
            self._validate_unit(unit)

    def test_convert(self) -> None:
        """Test the convert method."""

        unit1 = MockUnits.BASE
        unit2 = MockUnits.MEGABASE

        with (
            patch(
                "asusrouter.tools.units.UnitConverterBase._validate_unit",
            ) as mock_validate_unit,
            patch(
                "asusrouter.tools.units.UnitConverterBase.converter_factory",
            ) as mock_converter_factory,
        ):
            self.convert(1.0, unit1, unit2)

            assert mock_validate_unit.call_count == 2  # noqa: PLR2004
            assert mock_validate_unit.call_args_list[0][0] == (unit1,)
            assert mock_validate_unit.call_args_list[1][0] == (unit2,)

            mock_converter_factory.assert_called_once_with(unit1, unit2)

    def test_convert_to_base(self) -> None:
        """Test the convert_to_base method."""

        # Clear the cache
        self.converter_factory.cache_clear()

        value = 1.0
        unit = MockUnits.MEGABASE

        with (
            patch(
                "asusrouter.tools.units.UnitConverterBase._validate_unit",
            ) as mock_validate_unit,
            patch(
                "asusrouter.tools.units.UnitConverterBase.converter_factory",
            ) as mock_converter_factory,
        ):
            result = self.convert_to_base(value, unit)

            mock_validate_unit.assert_called_once_with(unit)
            mock_converter_factory.assert_called_once_with(
                unit, self.UNIT_BASE
            )

            assert result == mock_converter_factory.return_value(value)

    def test_convert_to_base_already_base(self) -> None:
        """Test the convert_to_base method when the unit is the base unit."""

        value = 1.0
        unit = MockUnits.BASE

        with (
            patch(
                "asusrouter.tools.units.UnitConverterBase._validate_unit",
            ) as mock_validate_unit,
            patch(
                "asusrouter.tools.units.UnitConverterBase.converter_factory",
            ) as mock_converter_factory,
        ):
            result = self.convert_to_base(value, unit)

            mock_validate_unit.assert_called_once_with(unit)
            mock_converter_factory.assert_not_called()

            assert result == value

    def test_converter_factory(self) -> None:
        """Test the converter factory method."""

        # Clear the cache
        self.converter_factory.cache_clear()

        unit1 = MockUnits.BASE
        unit2 = MockUnits.MEGABASE

        with patch(
            "asusrouter.tools.units.UnitConverterBase._get_ratios",
            return_value=(1.0, 2.0),
        ) as mock_get_ratios:
            converter = self.converter_factory(unit1, unit2)

            mock_get_ratios.assert_called_once_with(unit1, unit2)
            assert converter is not None

    def test_converter_factory_identity_returns_identity(self) -> None:
        """When same units."""

        # Clear the cache
        self.converter_factory.cache_clear()

        fn = self.converter_factory(MockUnits.BASE, MockUnits.BASE)
        assert callable(fn)
        assert fn(1.234) == pytest.approx(1.234)

    def test_converter_factory_uses_get_ratios_and_is_cached(self) -> None:
        """converter_factory should call _get_ratios once and be cached."""

        # Clear the cache
        self.converter_factory.cache_clear()

        # arrange: make _get_ratios return predictable ratios
        with patch(
            "asusrouter.tools.units.UnitConverterBase._get_ratios",
            return_value=(2.0, 4.0),
        ) as mock_get:
            fn = self.converter_factory(MockUnits.BASE, MockUnits.MEGABASE)

            # _get_ratios must have been called once with the same enum args
            mock_get.assert_called_once_with(
                MockUnits.BASE, MockUnits.MEGABASE
            )

            # function must compute (value * from_ratio) / to_ratio
            assert fn(3.0) == pytest.approx((3.0 * 2.0) / 4.0)

            # reset mock and call converter_factory again with the same args:
            # due to lru_cache it should be cached ->
            mock_get.reset_mock()
            fn2 = self.converter_factory(MockUnits.BASE, MockUnits.MEGABASE)
            mock_get.assert_not_called()
            assert fn2 is fn

    def test_get_ratios(self) -> None:
        """Test the _get_ratios method."""

        unit1 = MockUnits.BASE
        unit2 = MockUnits.MEGABASE

        ratios = self._get_ratios(unit1, unit2)
        assert ratios == (MOCK_UNIT_RATIOS[unit1], MOCK_UNIT_RATIOS[unit2])

    def test_get_ratios_not_defined_ratio(self) -> None:
        """Test the _get_ratios method when the ratio is not defined."""

        unit1 = "Not a unit"
        unit2 = MockUnits.MEGABASE

        with pytest.raises(AsusRouterError, match="Unknown unit"):
            self._get_ratios(unit1, unit2)  # type: ignore[arg-type]

    def test_get_unit_ratio(self) -> None:
        """Test the get_unit_ratio method."""

        unit1 = MockUnits.BASE
        unit2 = MockUnits.MEGABASE

        with patch(
            "asusrouter.tools.units.UnitConverterBase._get_ratios",
            return_value=(2.0, 4.0),
        ) as mock_get_ratios:
            ratio = self.get_unit_ratio(unit1, unit2)

            mock_get_ratios.assert_called_once_with(unit1, unit2)
            assert ratio == 2.0 / 4.0
