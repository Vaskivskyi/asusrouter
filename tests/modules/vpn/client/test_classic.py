"""Tests for the classic (non-Fusion) VPN client backend."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.vpn.client import classic
from asusrouter.modules.vpn.enums import (
    ARVpnClientField,
    ARVpnProtocol,
    ARVpnState,
)
from asusrouter.tools.identifiers import IpAddress

# One active OpenVPN client (unit 1) and one WireGuard client (unit 2)
_DATA: dict[str, Any] = {
    "vpn_clientx_eas": "1,",
    "vpn_client1_state": "2",
    "vpn_client1_desc": "MyOVPN",
    "vpn_client1_addr": "vpn.host.test",
    "vpn_client1_port": "1194",
    "vpn_client1_username": "bob",
    "wgc2_enable": "1",
    "wgc2_addr": "10.6.0.2/32",
    "wgc2_ppub": "cHViZmFrZQ==",
    "wgc2_ep_addr": "203.0.113.9",
    "wgc2_ep_port": "51820",
    classic.STATUS_KEY: {
        "vpn_client1_status": (
            "REMOTE,198.51.100.7:1194,udp>Updated,2024-01-02 03:04:05"
            ">TUN/TAP read bytes,111>TUN/TAP write bytes,222"
            ">TCP/UDP read bytes,12345>TCP/UDP write bytes,678"
            ">Auth read bytes,333>pre-compress bytes,44>post-compress bytes,55"
            ">pre-decompress bytes,66>post-decompress bytes,77>END"
        ),
        "vpn_client1_ip": "10.8.0.6",
    },
}


class TestNvramItems:
    """Tests for nvram_items."""

    def test_contains(self) -> None:
        """Items cover per-unit OpenVPN and WireGuard clients."""

        keys = [item.as_hook()[1] for item in classic.nvram_items()]
        assert "vpn_clientx_eas" in keys
        assert "vpn_client1_state" in keys
        assert "vpn_client1_desc" in keys
        assert "wgc1_enable" in keys
        assert "wgc5_priv" in keys


class TestEnabledUnits:
    """Tests for _enabled_units."""

    def test_parses(self) -> None:
        """A comma list yields the set of active units."""

        assert classic._enabled_units({"vpn_clientx_eas": "1,3,"}) == {1, 3}

    def test_absent(self) -> None:
        """No value yields an empty set."""

        assert classic._enabled_units({}) == set()


class TestClean:
    """Tests for _clean."""

    def test_placeholders(self) -> None:
        """Empty placeholders become None; real values pass through."""

        assert classic._clean("None") is None
        assert classic._clean("") is None
        assert classic._clean("10.0.0.1") == "10.0.0.1"


class TestIp:
    """Tests for _ip."""

    def test_unspecified_is_absent(self) -> None:
        """The all-zero address is treated as no address."""

        assert classic._ip("0.0.0.0") is None
        assert classic._ip("None") is None
        assert classic._ip("10.0.0.1") == IpAddress("10.0.0.1")


class TestParseStatus:
    """Tests for _parse_status."""

    def test_full(self) -> None:
        """Remote endpoint and transfer counters parse to typed fields."""

        fields = classic._parse_status(
            _DATA[classic.STATUS_KEY]["vpn_client1_status"]
        )
        assert fields[ARVpnClientField.REMOTE_ADDRESS] == IpAddress(
            "198.51.100.7"
        )
        assert fields[ARVpnClientField.REMOTE_PORT] == 1194
        assert fields[ARVpnClientField.RX_BYTES] == 12345
        assert fields[ARVpnClientField.TX_BYTES] == 678
        assert fields[ARVpnClientField.TUN_TAP_RX_BYTES] == 111
        assert fields[ARVpnClientField.TUN_TAP_TX_BYTES] == 222
        assert fields[ARVpnClientField.AUTH_RX_BYTES] == 333
        assert fields[ARVpnClientField.PRE_COMPRESS_BYTES] == 44
        assert fields[ARVpnClientField.POST_COMPRESS_BYTES] == 55
        assert fields[ARVpnClientField.PRE_DECOMPRESS_BYTES] == 66
        assert fields[ARVpnClientField.POST_DECOMPRESS_BYTES] == 77

    def test_remote_without_port(self) -> None:
        """A remote with no port maps only the address."""

        fields = classic._parse_status("REMOTE,198.51.100.7,udp>END")
        assert fields[ARVpnClientField.REMOTE_ADDRESS] == IpAddress(
            "198.51.100.7"
        )
        assert ARVpnClientField.REMOTE_PORT not in fields

    def test_placeholder(self) -> None:
        """A `None` status yields no fields."""

        assert classic._parse_status("None") == {}


class TestTranslate:
    """Tests for translate."""

    def test_idle(self) -> None:
        """A device with no configured clients yields an empty result."""

        idle = {classic.STATUS_KEY: {"vpn_client1_status": "None"}}
        assert classic.translate(idle) == {}

    def test_openvpn_profile(self) -> None:
        """The OpenVPN client carries nvram config, state and live stats."""

        ovpn = classic.translate(_DATA)[ARVpnProtocol.OPENVPN][1]
        assert ovpn[ARVpnClientField.NAME] == "MyOVPN"
        assert ovpn[ARVpnClientField.SERVER] == "vpn.host.test"
        assert ovpn[ARVpnClientField.USERNAME] == "bob"
        assert ovpn[ARVpnClientField.STATE] is ARVpnState.CONNECTED
        assert ovpn[ARVpnClientField.UNIT] == 1
        assert ovpn[ARVpnClientField.ENABLED] is True
        assert ovpn[ARVpnClientField.ADDRESS] == IpAddress("10.8.0.6")
        assert ovpn[ARVpnClientField.REMOTE_ADDRESS] == IpAddress(
            "198.51.100.7"
        )
        assert ovpn[ARVpnClientField.RX_BYTES] == 12345

    def test_openvpn_error_reason(self) -> None:
        """A failed OpenVPN client records the errno reason."""

        data = {"vpn_client1_state": "-1", "vpn_client1_errno": "2"}
        ovpn = classic.translate(data)[ARVpnProtocol.OPENVPN][1]
        assert ovpn[ARVpnClientField.STATE] is ARVpnState.ERROR
        assert ovpn[ARVpnClientField.STATE_REASON] == 2

    def test_wireguard_profile(self) -> None:
        """The WireGuard client carries its `wgc` config and enable flag."""

        wg = classic.translate(_DATA)[ARVpnProtocol.WIREGUARD][2]
        assert wg[ARVpnClientField.ENABLED] is True
        assert wg[ARVpnClientField.UNIT] == 2
        assert wg[ARVpnClientField.ENDPOINT_ADDRESS] == IpAddress(
            "203.0.113.9"
        )

    def test_disabled_wireguard_still_listed(self) -> None:
        """A configured-but-disabled WireGuard unit is still reported."""

        wg = classic.translate({"wgc3_enable": "0"})[ARVpnProtocol.WIREGUARD][
            3
        ]
        assert wg[ARVpnClientField.ENABLED] is False
