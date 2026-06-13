"""Units tools."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from functools import cache
from typing import ClassVar

from asusrouter.error import AsusRouterError


class UnitOfData(StrEnum):
    """Units of data."""

    # Base unit
    BIT = "b"
    BYTE = "B"
    # Base 10
    KILOBIT = "kb"
    MEGABIT = "Mb"
    GIGABIT = "Gb"
    TERABIT = "Tb"
    KILOBYTE = "KB"
    MEGABYTE = "MB"
    GIGABYTE = "GB"
    TERABYTE = "TB"
    # Base 2 (native Asus Type)
    KIBIBIT = "Kib"
    MEBIBIT = "Mib"
    GIBIBIT = "Gib"
    TEBIBIT = "Tib"
    KIBIBYTE = "KiB"
    MEBIBYTE = "MiB"
    GIBIBYTE = "GiB"
    TEBIBYTE = "TiB"


class UnitOfDataRate(StrEnum):
    """Units of data rate."""

    # Base unit
    BIT_PER_SECOND = "bps"
    BYTE_PER_SECOND = "Bps"
    # Base 10
    KILOBIT_PER_SECOND = "kbps"
    MEGABIT_PER_SECOND = "Mbps"
    GIGABIT_PER_SECOND = "Gbps"
    TERABIT_PER_SECOND = "Tbps"
    KILOBYTE_PER_SECOND = "KBps"
    MEGABYTE_PER_SECOND = "MBps"
    GIGABYTE_PER_SECOND = "GBps"
    TERABYTE_PER_SECOND = "TBps"
    # Base 2 (native Asus Type)
    KIBIBIT_PER_SECOND = "Kibps"
    MEBIBIT_PER_SECOND = "Mibps"
    GIBIBIT_PER_SECOND = "Gibps"
    TEBIBIT_PER_SECOND = "Tibps"
    KIBIBYTE_PER_SECOND = "KiBps"
    MEBIBYTE_PER_SECOND = "MiBps"
    GIBIBYTE_PER_SECOND = "GiBps"
    TEBIBYTE_PER_SECOND = "TiBps"


class UnitConverterBase:
    """AsusRouter Unit Converter."""

    UNIT_CLASS: ClassVar[str]
    _UNIT_RATIO: ClassVar[dict[StrEnum, float]]

    @classmethod
    def _validate_unit(cls, unit: StrEnum) -> None:
        """Validate that a unit is supported."""

        if unit not in cls._UNIT_RATIO:
            raise AsusRouterError(
                f"Unknown unit `{unit}` encountered during "
                f"conversion of `{cls.UNIT_CLASS}`"
            )

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


class DataUnitConverter(UnitConverterBase):
    """Data Unit Converter."""

    UNIT_CLASS = "data"

    _UNIT_RATIO = {
        UnitOfData.BIT: 1,
        UnitOfData.BYTE: 8,
        UnitOfData.KILOBIT: 1e3,
        UnitOfData.MEGABIT: 1e6,
        UnitOfData.GIGABIT: 1e9,
        UnitOfData.TERABIT: 1e12,
        UnitOfData.KIBIBIT: 2**10,
        UnitOfData.MEBIBIT: 2**20,
        UnitOfData.GIBIBIT: 2**30,
        UnitOfData.TEBIBIT: 2**40,
        UnitOfData.KILOBYTE: 8e3,
        UnitOfData.MEGABYTE: 8e6,
        UnitOfData.GIGABYTE: 8e9,
        UnitOfData.TERABYTE: 8e12,
        UnitOfData.KIBIBYTE: 2**13,
        UnitOfData.MEBIBYTE: 2**23,
        UnitOfData.GIBIBYTE: 2**33,
        UnitOfData.TEBIBYTE: 2**43,
    }


class DataRateUnitConverter(UnitConverterBase):
    """Data Rate Unit Converter."""

    UNIT_CLASS = "data_rate"

    _UNIT_RATIO = {
        UnitOfDataRate.BIT_PER_SECOND: 1,
        UnitOfDataRate.BYTE_PER_SECOND: 8,
        UnitOfDataRate.KILOBIT_PER_SECOND: 1e3,
        UnitOfDataRate.MEGABIT_PER_SECOND: 1e6,
        UnitOfDataRate.GIGABIT_PER_SECOND: 1e9,
        UnitOfDataRate.TERABIT_PER_SECOND: 1e12,
        UnitOfDataRate.KIBIBIT_PER_SECOND: 2**10,
        UnitOfDataRate.MEBIBIT_PER_SECOND: 2**20,
        UnitOfDataRate.GIBIBIT_PER_SECOND: 2**30,
        UnitOfDataRate.TEBIBIT_PER_SECOND: 2**40,
        UnitOfDataRate.KILOBYTE_PER_SECOND: 8e3,
        UnitOfDataRate.MEGABYTE_PER_SECOND: 8e6,
        UnitOfDataRate.GIGABYTE_PER_SECOND: 8e9,
        UnitOfDataRate.TERABYTE_PER_SECOND: 8e12,
        UnitOfDataRate.KIBIBYTE_PER_SECOND: 2**13,
        UnitOfDataRate.MEBIBYTE_PER_SECOND: 2**23,
        UnitOfDataRate.GIBIBYTE_PER_SECOND: 2**33,
        UnitOfDataRate.TEBIBYTE_PER_SECOND: 2**43,
    }
