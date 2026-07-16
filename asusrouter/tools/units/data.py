"""Data units for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.tools.units.base import UnitConverterBase


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
