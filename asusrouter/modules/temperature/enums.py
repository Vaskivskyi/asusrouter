"""Temperature enums for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARTemperatureType(FromStrMixin, StrEnum):
    """AsusRouter temperature data type."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    CPU = "cpu"
    RADIO_2G1 = "radio_2g1"
    RADIO_2G2 = "radio_2g2"
    RADIO_5G1 = "radio_5g1"
    RADIO_5G2 = "radio_5g2"
    RADIO_6G1 = "radio_6g1"
    RADIO_6G2 = "radio_6g2"


__all__ = [
    "ARTemperatureType",
]
