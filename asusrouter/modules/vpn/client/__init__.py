"""VPN client module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.vpn.client.action import ARVpnClientAction
from asusrouter.modules.vpn.client.source import (
    ARVpnClientSource,
    ARVpnClientSourceUniversal,
    fetch_state,
    translate_state,
)

__all__ = [
    "ARVpnClientAction",
    "ARVpnClientSource",
    "ARVpnClientSourceUniversal",
    "fetch_state",
    "translate_state",
]
