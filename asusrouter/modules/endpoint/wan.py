"""WAN endpoint module."""

from __future__ import annotations

from enum import Enum


class AsusDualWAN(str, Enum):
    """Dual WAN class."""

    FAILOVER = "fo"
    FALLBACK = "fb"
    LOAD_BALANCE = "lb"
