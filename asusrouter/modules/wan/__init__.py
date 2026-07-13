"""WAN module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.wan.enums import ARDualWanMode, ARWANCapability
from asusrouter.modules.wan.source import (
    ARDualWan,
    ARWan,
    ARWanAddress,
    ARWanAggregation,
    ARWanPPP,
    ARWanSoftwire,
    ARWanSource,
    ARWanSourceUniversal,
    ARWanUnit,
    ARWanVlan,
    ARWanWatchdog,
    get_state,
    translate_state,
)

__all__ = [
    "ARDualWan",
    "ARDualWanMode",
    "ARWANCapability",
    "ARWan",
    "ARWanAddress",
    "ARWanAggregation",
    "ARWanPPP",
    "ARWanSoftwire",
    "ARWanSource",
    "ARWanSourceUniversal",
    "ARWanUnit",
    "ARWanVlan",
    "ARWanWatchdog",
    "get_state",
    "translate_state",
]
