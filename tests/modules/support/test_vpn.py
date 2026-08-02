"""Tests for the support vpn module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.vpn import (
    translate_vpn,
    translate_vpn_capabilities,
)
from asusrouter.modules.vpn.enums import ARVpnCapability


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.VPN_OPENVPN.value: 1}, True),
        ({ARSupportValue.VPN_IPSEC.value: 5}, True),
        ({ARSupportValue.VPN_OPENVPN.value: 0}, False),
        ({}, False),
    ],
)
def test_translate_vpn(data: Any, expected: bool) -> None:
    """Test translate_vpn reports any VPN capability."""

    assert translate_vpn(data) is expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        # Non-Fusion capabilities map to True, no connection detail
        (
            {ARSupportValue.VPN_CLIENT.value: 1},
            {ARVpnCapability.CLIENT: True},
        ),
        (
            {ARSupportValue.VPN_IPSEC.value: 5},
            {ARVpnCapability.IPSEC: True},
        ),
        # Fusion pulls in FUSION_CONNECTIONS with its int value
        (
            {
                ARSupportValue.VPN_FUSION.value: 1,
                ARSupportValue.VPN_FUSION_MAX_CONNECTIONS.value: 4,
            },
            {
                ARVpnCapability.FUSION: True,
                ARVpnCapability.FUSION_CONNECTIONS: 4,
            },
        ),
        # Fusion with 0 -> firmware default 2
        (
            {ARSupportValue.VPN_FUSION.value: 1},
            {
                ARVpnCapability.FUSION: True,
                ARVpnCapability.FUSION_CONNECTIONS: 2,
            },
        ),
        # No Fusion -> the connection flag is ignored
        (
            {ARSupportValue.VPN_FUSION_MAX_CONNECTIONS.value: 4},
            {},
        ),
        ({}, {}),
    ],
)
def test_translate_vpn_capabilities(
    data: Any, expected: dict[ARVpnCapability, bool | int]
) -> None:
    """Test translate_vpn_capabilities maps capabilities and Fusion detail."""

    assert translate_vpn_capabilities(data) == expected
