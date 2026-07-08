"""VPN client module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.vpn.client.source import (
    ARVpnClientSource,
    ARVpnClientSourceUniversal,
    get_state,
    translate_state,
)

__all__ = [
    "ARVpnClientSource",
    "ARVpnClientSourceUniversal",
    "get_state",
    "translate_state",
]
