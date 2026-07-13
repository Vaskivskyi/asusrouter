"""Ping enums for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARPingStatus(FromStrMixin, StrEnum):
    """Ping run status reported in nvram `dns_ping_state`."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    FINISHED = "3"


__all__ = [
    "ARPingStatus",
]
