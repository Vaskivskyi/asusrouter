"""WAN endpoint module."""

from __future__ import annotations

from enum import StrEnum


class AsusDualWAN(StrEnum):
    """Dual WAN class."""

    FAILOVER = "fo"
    FALLBACK = "fb"
    LOAD_BALANCE = "lb"
