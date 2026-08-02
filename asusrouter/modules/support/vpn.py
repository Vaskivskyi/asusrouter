"""Supported VPN."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.vpn.enums import ARVpnCapability
from asusrouter.tools.converters.raw import raw_to_int
from asusrouter.tools.readers import is_true_in_dict

# Firmware default active connections when Fusion reports 0
_VPN_FUSION_DEFAULT_CONNECTIONS = 2

_CAPABILITY_FLAGS = {
    ARSupportValue.VPN_CLIENT.value: ARVpnCapability.CLIENT,
    ARSupportValue.VPN_FUSION.value: ARVpnCapability.FUSION,
    ARSupportValue.VPN_IPSEC.value: ARVpnCapability.IPSEC,
    ARSupportValue.VPN_OPENVPN.value: ARVpnCapability.OPENVPN,
    ARSupportValue.VPN_PPTP.value: ARVpnCapability.PPTP,
    ARSupportValue.VPN_WIREGUARD.value: ARVpnCapability.WIREGUARD,
}


def _fusion_connections(data: dict[str, Any]) -> int:
    """Max Fusion connections active at once; 0 reports the default."""

    value = raw_to_int(
        data.get(ARSupportValue.VPN_FUSION_MAX_CONNECTIONS.value)
    )
    return value or _VPN_FUSION_DEFAULT_CONNECTIONS


def translate_vpn_capabilities(
    data: dict[str, Any],
) -> dict[ARVpnCapability, bool | int]:
    """Map advertised VPN capabilities; FUSION_CONNECTIONS carries an int."""

    capabilities: dict[ARVpnCapability, bool | int] = {
        capability: True
        for key, capability in _CAPABILITY_FLAGS.items()
        if is_true_in_dict(key, data)
    }
    if ARVpnCapability.FUSION in capabilities:
        capabilities[ARVpnCapability.FUSION_CONNECTIONS] = _fusion_connections(
            data
        )
    return capabilities


def translate_vpn(data: dict[str, Any]) -> bool:
    """Report whether the device advertises any VPN capability."""

    return bool(translate_vpn_capabilities(data))
