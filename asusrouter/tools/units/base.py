"""Base unit converter for AsusRouter."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from functools import cache
from typing import Any, ClassVar

from asusrouter.error import AsusRouterError
from asusrouter.tools.converters_v2.raw import raw_to_float
from asusrouter.tools.types import ARCallableType


class UnitConverterBase:
    """AsusRouter Unit Converter."""

    UNIT_CLASS: ClassVar[str]
    _UNIT_RATIO: ClassVar[dict[StrEnum, float]]

    @classmethod
    @cache
    def get_unit_ratio(cls, from_unit: StrEnum, to_unit: StrEnum) -> float:
        """Get unit ratio between units of measurement."""

        try:
            return cls._UNIT_RATIO[from_unit] / cls._UNIT_RATIO[to_unit]
        except KeyError as ex:
            raise AsusRouterError(
                f"Unknown unit `{ex.args[0]}` encountered during "
                f"conversion of `{cls.UNIT_CLASS}`"
            )

    @classmethod
    def convert(
        cls, value: float, from_unit: StrEnum, to_unit: StrEnum
    ) -> float:
        """Convert a value from one unit to another."""

        if from_unit == to_unit:
            return value
        return value * cls.get_unit_ratio(from_unit, to_unit)

    @classmethod
    def convert_to_base(cls, value: float, from_unit: StrEnum) -> float:
        """Convert a value to the base unit."""

        try:
            return value * cls._UNIT_RATIO[from_unit]
        except KeyError:
            raise AsusRouterError(
                f"Unknown unit `{from_unit}` encountered during "
                f"conversion of `{cls.UNIT_CLASS}`"
            )

    @classmethod
    @cache
    def converter_factory(
        cls, from_unit: StrEnum, to_unit: StrEnum
    ) -> Callable[[float], float]:
        """Create a conversion function from one unit to another."""

        if from_unit == to_unit:
            return lambda value: value

        factor = cls.get_unit_ratio(from_unit, to_unit)
        return lambda value: value * factor


def is_non_negative(value: Any) -> bool:
    """Check if the value is non-negative (unparseable values pass)."""

    fval = raw_to_float(value)
    return fval is None or fval >= 0


def read_as_base(
    converter: type[UnitConverterBase],
    units: StrEnum,
    check_calls: ARCallableType | list[ARCallableType] | None = None,
    fallback_value: float = 0.0,
) -> ARCallableType:
    """Create a reader from the units to the base."""

    if not isinstance(converter, type) or not issubclass(
        converter, UnitConverterBase
    ):
        raise TypeError("Converter must be a subclass of UnitConverterBase")

    # Convert single check call to a list
    if check_calls is not None and not isinstance(check_calls, list):
        check_calls = [check_calls]

    def reader(value: Any) -> float:
        """Read the value as a base unit."""

        fval = raw_to_float(value)

        # Convert to base if all the checks passed
        if fval is not None and (
            check_calls is None or all(call(fval) for call in check_calls)
        ):
            return converter.convert_to_base(fval, units)

        return fallback_value

    return reader
