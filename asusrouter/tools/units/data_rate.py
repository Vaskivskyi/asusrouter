"""Data rate units for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.tools.types import ARCallableType
from asusrouter.tools.units.base import (
    UnitConverterBase,
    is_non_negative,
    read_as_base,
)


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


def read_data_rate(units: UnitOfDataRate) -> ARCallableType:
    """Read data rate values from the specified unit type."""

    return read_as_base(DataRateUnitConverter, units, is_non_negative, 0.0)
