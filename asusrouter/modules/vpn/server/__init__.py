"""VPN server module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.vpn.server.action import ARVpnServerAction
from asusrouter.modules.vpn.server.source import (
    ARVpnServerSource,
    ARVpnServerSourceUniversal,
    fetch_state,
    translate_state,
)

__all__ = [
    "ARVpnServerAction",
    "ARVpnServerSource",
    "ARVpnServerSourceUniversal",
    "fetch_state",
    "translate_state",
]
