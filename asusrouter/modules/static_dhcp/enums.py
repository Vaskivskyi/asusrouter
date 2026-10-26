"""Static DHCP enums for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARStaticDHCPCommand(FromStrMixin, StrEnum):
    """The mutation a static DHCP action performs."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    ADD = "add"
    REMOVE = "remove"
    SET = "set"
    STATE = "state"


class ARStaticDHCPField(FromStrMixin, StrEnum):
    """Keys of the static DHCP data dict."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    COMPLETE = "complete"
    LEASES = "leases"
    STATE = "state"


class ARStaticDHCPLayout(FromStrMixin, StrEnum):
    """NVRAM column layout used by one lease row."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    LEGACY = "legacy"
    MODERN = "modern"


__all__ = [
    "ARStaticDHCPCommand",
    "ARStaticDHCPField",
    "ARStaticDHCPLayout",
]
