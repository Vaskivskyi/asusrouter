"""Flags for the firmware module."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARFirmwareType(FromStrMixin, StrEnum):
    """Firmware types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    STOCK = "stock"
    MERLIN = "merlin"
    GNUTON = "gnuton"


AR_FW_MERLIN_LIKE: frozenset[ARFirmwareType] = frozenset(
    {ARFirmwareType.MERLIN, ARFirmwareType.GNUTON}
)
