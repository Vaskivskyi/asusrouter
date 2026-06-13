"""Tests for the unit tools."""

from __future__ import annotations

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

        with patch(
            "asusrouter.tools.units.UnitConverterBase.get_unit_ratio",
            return_value=0.5,
        ) as mock_get_unit_ratio:
            result = self.convert(2.0, unit1, unit2)

            mock_get_unit_ratio.assert_called_once_with(unit1, unit2)
            assert result == pytest.approx(2.0 * 0.5)

    def test_convert_identity(self) -> None:
        """Test convert returns value unchanged when units are equal."""

        result = self.convert(42.0, MockUnits.BASE, MockUnits.BASE)
        assert result == pytest.approx(42.0)

    @pytest.mark.parametrize(
        ("value", "unit", "expected"),
        [
            (1.0, MockUnits.BASE, 1.0),
            (1.0, MockUnits.MEGABASE, float(10**6)),
            (2.5, MockUnits.TERABASE, 2.5 * 10**12),
        ],
    )
    def test_convert_to_base(
        self, value: float, unit: MockUnits, expected: float
    ) -> None:
        """Test the convert_to_base method."""

        result = self.convert_to_base(value, unit)
        assert result == pytest.approx(expected)

    def test_convert_to_base_unknown_unit(self) -> None:
        """Test convert_to_base raises AsusRouterError for unknown units."""

        with pytest.raises(AsusRouterError, match="Unknown unit"):
            self.convert_to_base(1.0, "not_a_unit")  # type: ignore[arg-type]

    def test_converter_factory(self) -> None:
        """Test the converter factory method."""

        self.converter_factory.cache_clear()

        fn = self.converter_factory(MockUnits.BASE, MockUnits.MEGABASE)
        assert callable(fn)
        assert fn(3.0) == pytest.approx(
            3.0
            * MOCK_UNIT_RATIOS[MockUnits.BASE]
            / MOCK_UNIT_RATIOS[MockUnits.MEGABASE]
        )

    def test_converter_factory_identity_returns_identity(self) -> None:
        """When same units."""

        self.converter_factory.cache_clear()

        fn = self.converter_factory(MockUnits.BASE, MockUnits.BASE)
        assert callable(fn)
        assert fn(1.234) == pytest.approx(1.234)

    def test_converter_factory_is_cached(self) -> None:
        """converter_factory result is cached per unit pair."""

        self.converter_factory.cache_clear()

        fn = self.converter_factory(MockUnits.BASE, MockUnits.MEGABASE)
        fn2 = self.converter_factory(MockUnits.BASE, MockUnits.MEGABASE)
        assert fn2 is fn

    def test_converter_factory_unknown_unit(self) -> None:
        """converter_factory raises for units not in ratio table."""

        self.converter_factory.cache_clear()

        with pytest.raises(AsusRouterError, match="Unknown unit"):
            self.converter_factory("not_a_unit", MockUnits.MEGABASE)  # type: ignore[arg-type]

    def test_get_unit_ratio(self) -> None:
        """Test the get_unit_ratio method."""

        self.get_unit_ratio.cache_clear()

        unit1 = MockUnits.BASE
        unit2 = MockUnits.MEGABASE

        ratio = self.get_unit_ratio(unit1, unit2)
        assert ratio == pytest.approx(
            MOCK_UNIT_RATIOS[unit1] / MOCK_UNIT_RATIOS[unit2]
        )

    def test_get_unit_ratio_unknown_unit(self) -> None:
        """Test get_unit_ratio raises AsusRouterError for unknown units."""

        self.get_unit_ratio.cache_clear()

        with pytest.raises(AsusRouterError, match="Unknown unit"):
            self.get_unit_ratio("not_a_unit", MockUnits.MEGABASE)  # type: ignore[arg-type]

    def test_get_unit_ratio_is_cached(self) -> None:
        """Test get_unit_ratio result is cached per unit pair."""

        self.get_unit_ratio.cache_clear()

        r1 = self.get_unit_ratio(MockUnits.BASE, MockUnits.MEGABASE)
        r2 = self.get_unit_ratio(MockUnits.BASE, MockUnits.MEGABASE)
        assert r1 == r2
