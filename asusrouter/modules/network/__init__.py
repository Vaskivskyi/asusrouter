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
)
from asusrouter.modules.network.handle import ARNetworkHandle
from asusrouter.modules.network.source import (
    ARNetworkSource,
    ARNetworkSourceUniversal,
    get_state,
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
    "find_handle_by_ssid",
    "get_state",
    "run_action",
    "translate_state",
]
