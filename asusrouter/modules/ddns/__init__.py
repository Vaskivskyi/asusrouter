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
from asusrouter.modules.ddns.legacy import (
    DDNS_HINT_MAP,
    DDNS_STATUS_ACTIVE,
    DDNS_STATUS_HINT,
    AsusDDNS,
    DDNSStatusCode,
    DDNSStatusHint,
    process_ddns,
    read_ddns_status_code,
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
    "DDNS_HINT_MAP",
    "DDNS_REQUEST",
    "DDNS_STATUS_ACTIVE",
    "DDNS_STATUS_HINT",
    "ARDdnsAction",
    "ARDdnsCommand",
    "ARDdnsConfig",
    "ARDdnsField",
    "ARDdnsServer",
    "ARDdnsSource",
    "ARDdnsSourceUniversal",
    "ARDdnsStatus",
    "AsusDDNS",
    "DDNSStatusCode",
    "DDNSStatusHint",
    "get_state",
    "process_ddns",
    "read_ddns_status_code",
    "read_status",
    "run_action",
    "translate_state",
]
