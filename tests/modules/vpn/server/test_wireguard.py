"""Tests for the WireGuard server backend."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.common.command import ARService
from asusrouter.modules.vpn.enums import (
    ARVpnClientField,
    ARVpnServerField,
    ARVpnState,
)
from asusrouter.modules.vpn.server import wireguard as wg
from asusrouter.tools.identifiers import IpInterface, Password

# Server settings + one peer, mirroring the real (encoded) nvram shape
_DATA: dict[str, Any] = {
    "wgs_enable": "1",
    "wgs_addr": "10.55.0.1/24",
    "wgs_port": "443",
    "wgs_dns": "1",
    "wgs_nat6": "1",
    "wgs_psk": "1",
    "wgs_alive": "25",
    "wgs_lanaccess": "1",
    "wgs_pub": "PUBKEYVALUE=",
    "wgs_priv": "PRIVKEYVALUE=",
    "wgs1_c1_enable": "1",
    "wgs1_c1_name": "My%2FPeer",
    "wgs1_c1_addr": "10%2E55%2E0%2E24%2F32",
    "wgs1_c1_aips": "10%2E55%2E0%2E24%2F32",
    "wgs1_c1_caips": "0%2E0%2E0%2E0%2F0",
    wg.HOOK.value: {"client_status": [{"index": 1, "status": 1}]},
}


class TestDecode:
    """Tests for the URL-decode helpers."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("My%2FPeer", "My/Peer"),
            ("plain", "plain"),
            (None, None),
            ("", None),
        ],
    )
    def test_decode(self, value: Any, expected: Any) -> None:
        """Percent-encoded strings decode; empty/None yield None."""

        assert wg._decode(value) == expected

    def test_decode_interfaces(self) -> None:
        """Encoded interface lists decode and parse."""

        result = wg._decode_interfaces("10%2E0%2E0%2E1%2F32")
        assert [str(i) for i in result] == ["10.0.0.1/32"]

    def test_decode_interfaces_none(self) -> None:
        """None decodes to an empty list."""

        assert wg._decode_interfaces(None) == []


class TestNvramKeys:
    """Tests for nvram_keys."""

    def test_contains_settings_and_peers(self) -> None:
        """Keys cover settings plus every peer slot."""

        keys = wg.nvram_keys()
        assert "wgs_enable" in keys
        assert "wgs_priv" in keys
        assert "wgs1_c1_name" in keys
        assert f"wgs1_c{wg.MAX_PEERS}_caips" in keys


class TestConvert:
    """Tests for _convert."""

    def test_none_empty(self) -> None:
        """None/empty are absent."""

        assert wg._convert(None, str) is None
        assert wg._convert("", str) is None

    def test_value_and_empty_list(self) -> None:
        """Values pass through; empty-list results are absent."""

        assert wg._convert("5", int) == 5
        assert wg._convert("x", lambda _: []) is None


class TestPeerStatus:
    """Tests for _peer_status."""

    def test_non_dict_hook(self) -> None:
        """A missing/invalid hook yields no status."""

        assert wg._peer_status({}) == {}

    def test_maps_states(self) -> None:
        """Status 1 -> CONNECTED, otherwise DISCONNECTED; bad index skipped."""

        data = {
            wg.HOOK.value: {
                "client_status": [
                    {"index": 1, "status": 1},
                    {"index": 2, "status": 0},
                    {"index": None, "status": 1},
                ]
            }
        }
        assert wg._peer_status(data) == {
            1: ARVpnState.CONNECTED,
            2: ARVpnState.DISCONNECTED,
        }


class TestPeer:
    """Tests for _peer."""

    def test_empty_slot(self) -> None:
        """An empty slot returns None."""

        assert wg._peer({}, 5, {}) is None

    def test_populated_without_status(self) -> None:
        """A peer with no live status omits STATE."""

        peer = wg._peer(_DATA, 1, {})
        assert peer is not None
        assert ARVpnClientField.STATE not in peer

    def test_populated_with_status(self) -> None:
        """A peer with live status carries STATE."""

        peer = wg._peer(_DATA, 1, {1: ARVpnState.CONNECTED})
        assert peer[ARVpnClientField.STATE] is ARVpnState.CONNECTED


class TestTranslate:
    """Tests for translate."""

    def test_no_settings(self) -> None:
        """No server settings yields an empty result."""

        assert wg.translate({}) == {}

    def test_full(self) -> None:
        """A full payload maps server fields, keys, and the decoded peer."""

        server = wg.translate(_DATA)[wg.UNIT]

        assert server[ARVpnServerField.ENABLED] is True
        assert server[ARVpnServerField.ADDRESS] == IpInterface("10.55.0.1/24")
        assert server[ARVpnServerField.PORT] == 443
        assert server[ARVpnServerField.ALLOW_DNS] is True
        assert server[ARVpnServerField.PSK] is True
        assert server[ARVpnServerField.KEEPALIVE] == 25
        assert server[ARVpnServerField.PUBLIC_KEY] == "PUBKEYVALUE="
        assert isinstance(server[ARVpnServerField.PRIVATE_KEY], Password)

        peer = server[ARVpnServerField.CLIENTS][0]
        assert peer[ARVpnClientField.NAME] == "My/Peer"
        assert peer[ARVpnClientField.ADDRESS] == [IpInterface("10.55.0.24/32")]
        assert peer[ARVpnClientField.CLIENT_ALLOWED_IPS] == [
            IpInterface("0.0.0.0/0")
        ]
        assert peer[ARVpnClientField.STATE] is ARVpnState.CONNECTED

    def test_no_peers(self) -> None:
        """Server without peers omits the CLIENTS key."""

        server = wg.translate({"wgs_enable": "1"})[wg.UNIT]
        assert ARVpnServerField.CLIENTS not in server


class TestBuildTogglePayload:
    """Tests for build_toggle_payload."""

    def test_enable(self) -> None:
        """Enabling restarts the server and dnsmasq, flags nvram on."""

        services, arguments = wg.build_toggle_payload(1, True)
        assert services == [
            ARService.WIREGUARD_SERVER_RESTART,
            ARService.DNS_RESTART,
        ]
        assert arguments == {"wgs_enable": 1, "wgs_unit": 1, "id": 1}

    def test_disable(self) -> None:
        """Disabling uses the same services and flags nvram off."""

        services, arguments = wg.build_toggle_payload(2, False)
        assert services == [
            ARService.WIREGUARD_SERVER_RESTART,
            ARService.DNS_RESTART,
        ]
        assert arguments == {"wgs_enable": 0, "wgs_unit": 2, "id": 2}
