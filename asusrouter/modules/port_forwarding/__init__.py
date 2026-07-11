"""Port forwarding module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.port_forwarding.action import (
    ARPortForwardingAction,
    ARPortForwardingRule,
    run_action,
)
from asusrouter.modules.port_forwarding.enums import (
    ARPortForwardingCommand,
    ARPortForwardingField,
    ARPortForwardingProtocol,
)
from asusrouter.modules.port_forwarding.legacy import (
    KEY_PORT_FORWARDING_LIST,
    KEY_PORT_FORWARDING_STATE,
    AsusPortForwarding,
    PortForwardingRule,
    set_state,
)
from asusrouter.modules.port_forwarding.source import (
    ARPortForwardingSource,
    ARPortForwardingSourceUniversal,
    get_state,
    serialize_rules,
    translate_state,
)

__all__ = [
    "KEY_PORT_FORWARDING_LIST",
    "KEY_PORT_FORWARDING_STATE",
    "ARPortForwardingAction",
    "ARPortForwardingCommand",
    "ARPortForwardingField",
    "ARPortForwardingProtocol",
    "ARPortForwardingRule",
    "ARPortForwardingSource",
    "ARPortForwardingSourceUniversal",
    "AsusPortForwarding",
    "PortForwardingRule",
    "get_state",
    "run_action",
    "serialize_rules",
    "set_state",
    "translate_state",
]
