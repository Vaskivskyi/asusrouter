"""VPN module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.vpn.client import (
    ARVpnClientAction,
    ARVpnClientSource,
    ARVpnClientSourceUniversal,
)
from asusrouter.modules.vpn.enums import (
    ARVpnClientField,
    ARVpnPeerField,
    ARVpnProtocol,
    ARVpnRole,
    ARVpnServerField,
    ARVpnState,
)
from asusrouter.modules.vpn.server import (
    ARVpnServerAction,
    ARVpnServerSource,
    ARVpnServerSourceUniversal,
)

__all__ = [
    "ARVpnClientAction",
    "ARVpnClientField",
    "ARVpnClientSource",
    "ARVpnClientSourceUniversal",
    "ARVpnPeerField",
    "ARVpnProtocol",
    "ARVpnRole",
    "ARVpnServerAction",
    "ARVpnServerField",
    "ARVpnServerSource",
    "ARVpnServerSourceUniversal",
    "ARVpnState",
]
