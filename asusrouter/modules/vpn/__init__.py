"""VPN module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.vpn.enums import (
    ARVpnClientField,
    ARVpnProtocol,
    ARVpnRole,
    ARVpnServerField,
    ARVpnState,
)
from asusrouter.modules.vpn.server import (
    ARVpnServerSource,
    ARVpnServerSourceUniversal,
)

__all__ = [
    "ARVpnClientField",
    "ARVpnProtocol",
    "ARVpnRole",
    "ARVpnServerField",
    "ARVpnServerSource",
    "ARVpnServerSourceUniversal",
    "ARVpnState",
]
