"""Firmware types."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARFirmwareType(FromStrMixin, StrEnum):
    """Firmware types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    GNUTON = "gnuton"
    MERLIN = "merlin"
    STOCK = "stock"


AR_FW_MERLIN_LIKE: frozenset[ARFirmwareType] = frozenset(
    {ARFirmwareType.MERLIN, ARFirmwareType.GNUTON}
)
