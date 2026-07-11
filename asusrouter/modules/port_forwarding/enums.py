"""Port forwarding enums for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARPortForwardingCommand(FromStrMixin, StrEnum):
    """The mutation an action performs on port forwarding."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    ADD = "add"
    REMOVE = "remove"
    SET = "set"
    STATE = "state"


class ARPortForwardingProtocol(FromStrMixin, StrEnum):
    """Port forwarding rule protocol. Values are the device nvram strings."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    BOTH = "BOTH"
    OTHER = "OTHER"  # raw IP protocol number
    TCP = "TCP"
    UDP = "UDP"


class ARPortForwardingField(FromStrMixin, StrEnum):
    """Keys of the port forwarding data dict."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    EXTERNAL_PORT = "external_port"  # None when protocol is OTHER
    INTERNAL_IP = "internal_ip"
    INTERNAL_PORT = "internal_port"
    NAME = "name"
    PROTOCOL = "protocol"
    PROTOCOL_NUMBER = "protocol_number"  # set only when protocol is OTHER
    RULES = "rules"
    SOURCE_IP = "source_ip"
    STATE = "state"  # master port forwarding on/off
    WAN_UNIT = "wan_unit"  # 0 primary, 1 secondary (dual-WAN load-balance)


__all__ = [
    "ARPortForwardingCommand",
    "ARPortForwardingField",
    "ARPortForwardingProtocol",
]
