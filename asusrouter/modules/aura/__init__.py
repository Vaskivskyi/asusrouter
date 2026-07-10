"""Aura module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.aura.action import ARAuraAction
from asusrouter.modules.aura.enums import ARAuraField, ARAuraScheme
from asusrouter.modules.aura.legacy import (
    AsusAura,
    AsusAuraColor,
    process_aura,
    set_state,
)
from asusrouter.modules.aura.source import (
    ARAuraSource,
    ARAuraSourceUniversal,
    get_state,
    translate_state,
)

__all__ = [
    "ARAuraAction",
    "ARAuraField",
    "ARAuraScheme",
    "ARAuraSource",
    "ARAuraSourceUniversal",
    "AsusAura",
    "AsusAuraColor",
    "get_state",
    "process_aura",
    "set_state",
    "translate_state",
]
