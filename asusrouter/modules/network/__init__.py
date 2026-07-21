"""Network module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.network.action import (
    ARNetworkAction,
    find_handle_by_ssid,
    run_action,
)
from asusrouter.modules.network.enums import (
    ARNetworkBackend,
    ARNetworkField,
    ARNetworkSchedule,
    ARNetworkType,
    ARSDNCapability,
)
from asusrouter.modules.network.handle import ARNetworkHandle
from asusrouter.modules.network.source import (
    ARNetworkSource,
    ARNetworkSourceUniversal,
    fetch_state,
    translate_state,
)

__all__ = [
    "ARNetworkAction",
    "ARNetworkBackend",
    "ARNetworkField",
    "ARNetworkHandle",
    "ARNetworkSchedule",
    "ARNetworkSource",
    "ARNetworkSourceUniversal",
    "ARNetworkType",
    "ARSDNCapability",
    "find_handle_by_ssid",
    "fetch_state",
    "run_action",
    "translate_state",
]
