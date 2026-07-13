"""DDNS module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.ddns.action import (
    ARDdnsAction,
    ARDdnsConfig,
    run_action,
)
from asusrouter.modules.ddns.enums import (
    ACTIVE_STATUSES,
    ARDdnsCommand,
    ARDdnsField,
    ARDdnsServer,
    ARDdnsStatus,
)
from asusrouter.modules.ddns.source import (
    DDNS_REQUEST,
    ARDdnsSource,
    ARDdnsSourceUniversal,
    get_state,
    read_status,
    translate_state,
)

__all__ = [
    "ACTIVE_STATUSES",
    "DDNS_REQUEST",
    "ARDdnsAction",
    "ARDdnsCommand",
    "ARDdnsConfig",
    "ARDdnsField",
    "ARDdnsServer",
    "ARDdnsSource",
    "ARDdnsSourceUniversal",
    "ARDdnsStatus",
    "get_state",
    "read_status",
    "run_action",
    "translate_state",
]
