"""Tests for the OpenVPN server backend."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.common.command import ARService
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.firmware import ARFirmware
from asusrouter.modules.vpn.enums import (
    ARVpnPeerField,
    ARVpnServerField,
    ARVpnState,
)
from asusrouter.modules.vpn.server import openvpn as ovpn
from asusrouter.tools.identifiers import IpAddress, IpInterface, Password


def _identity(firmware: ARFirmware) -> ARDeviceIdentity:
    """Build an identity carrying the given firmware."""

    identity = ARDeviceIdentity()
    identity._firmware = firmware
    return identity


# Server settings + one account, mirroring the real nvram shape
_DATA: dict[str, Any] = {
    "VPNServer_enable": "1",
    "vpn_server_unit": "1",
    "vpn_server1_state": "2",
    "vpn_server1_errno": "0",
    "vpn_server2_state": "",
    "vpn_server_port": "1194",
    "vpn_server_proto": "tcp-server",
    "vpn_server_if": "tun",
    "vpn_server_crypt": "tls",
    "vpn_server_igncrt": "0",
    "vpn_server_sn": "10.8.0.0",
    "vpn_server_nm": "255.255.255.0",
    "vpn_server_dhcp": "1",
    "vpn_server_r1": "192.168.1.50",
    "vpn_server_r2": "192.168.1.55",
    "vpn_server_local": "10.8.0.1",
    "vpn_server_remote": "10.8.0.2",
    # HTML-encoded `<Surfie>` account
    "vpn_serverx_clientlist": "&#60Surfie&#62",
}


class TestServerEnabled:
    """Tests for server_enabled."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [("1", True), ("0", False), (None, False)],
    )
    def test_flag(self, value: Any, expected: bool) -> None:
        """VPNServer_enable drives the flag."""

        assert ovpn.server_enabled({"VPNServer_enable": value}) is expected


class TestNvramItems:
    """Tests for nvram_items."""

    def test_contains(self) -> None:
        """Items cover the enable flag, settings and per-unit state."""

        keys = [item.as_hook()[1] for item in ovpn.nvram_items()]
        assert "VPNServer_enable" in keys
        assert "vpn_serverx_clientlist" in keys
        assert "vpn_server1_state" in keys
        assert "vpn_server2_errno" in keys


class TestClients:
    """Tests for _clients account parsing."""

    def test_encoded_with_password(self) -> None:
        """An encoded `<user>pass` list parses to name + password."""

        result = ovpn._clients("&#60alice&#62secret&#60bob&#62")
        assert result[0][ARVpnPeerField.NAME] == "alice"
        assert isinstance(result[0][ARVpnPeerField.PASSWORD], Password)
        assert result[1][ARVpnPeerField.NAME] == "bob"
        assert ARVpnPeerField.PASSWORD not in result[1]

    def test_empty(self) -> None:
        """An empty list yields nothing."""

        assert ovpn._clients("") == []
        assert ovpn._clients(None) == []


class TestConnected:
    """Tests for _connected."""

    def test_non_dict(self) -> None:
        """A missing status yields no connected map."""

        assert ovpn._connected({}) == {}

    def test_maps_by_name(self) -> None:
        """Connected entries are keyed by name; nameless skipped."""

        data = {
            ovpn.CLIENT_STATUS_KEY: {
                "connected": [
                    {"name": "a", "vpn_ip": "10.8.0.2"},
                    {"vpn_ip": "10.8.0.9"},
                ]
            }
        }
        assert set(ovpn._connected(data)) == {"a"}


class TestLiveFields:
    """Tests for _live_fields."""

    def test_full(self) -> None:
        """Address and remote (ip:port) map to typed fields."""

        fields = ovpn._live_fields(
            {"vpn_ip": "10.8.0.2", "remote": "192.168.55.23:15620"}
        )
        assert fields[ARVpnPeerField.STATE] is ARVpnState.CONNECTED
        assert fields[ARVpnPeerField.ADDRESS] == [IpInterface("10.8.0.2/32")]
        assert fields[ARVpnPeerField.REMOTE_ADDRESS] == IpAddress(
            "192.168.55.23"
        )
        assert fields[ARVpnPeerField.REMOTE_PORT] == 15620

    def test_remote_without_port(self) -> None:
        """A remote with no port maps only the address."""

        fields = ovpn._live_fields({"remote": "192.168.55.23"})
        assert fields[ARVpnPeerField.REMOTE_ADDRESS] == IpAddress(
            "192.168.55.23"
        )
        assert ARVpnPeerField.REMOTE_PORT not in fields

    def test_no_live_data(self) -> None:
        """Missing address/remote leaves only STATE."""

        assert ovpn._live_fields({}) == {
            ARVpnPeerField.STATE: ARVpnState.CONNECTED
        }


class TestApplyStatus:
    """Tests for _apply_status."""

    def test_marks_and_appends(self) -> None:
        """Listed accounts are enriched; unlisted connected are appended."""

        clients = [{ARVpnPeerField.NAME: "alice"}]
        connected = {
            "alice": {"name": "alice"},
            "carol": {"name": "carol", "vpn_ip": "10.8.0.5"},
        }
        result = ovpn._apply_status(clients, connected)

        assert result[0][ARVpnPeerField.STATE] is ARVpnState.CONNECTED
        assert result[1][ARVpnPeerField.NAME] == "carol"
        assert result[1][ARVpnPeerField.ADDRESS] == [
            IpInterface("10.8.0.5/32")
        ]


class TestTranslate:
    """Tests for translate."""

    def test_active_unit(self) -> None:
        """The active unit carries settings, enable and accounts."""

        result = ovpn.translate(_DATA)
        server = result[1]

        assert server[ARVpnServerField.STATE] is ARVpnState.CONNECTED
        assert server[ARVpnServerField.ERRNO] == 0
        assert server[ARVpnServerField.ENABLED] is True
        assert server[ARVpnServerField.PORT] == 1194
        assert server[ARVpnServerField.PROTOCOL] == "tcp-server"
        assert server[ARVpnServerField.IGNORE_CERTIFICATE] is False
        assert server[ARVpnServerField.DHCP] is True
        assert server[ARVpnServerField.POOL_START] == IpAddress("192.168.1.50")
        assert server[ARVpnServerField.LOCAL_ADDRESS] == IpAddress("10.8.0.1")
        assert server[ARVpnServerField.CLIENTS][0][ARVpnPeerField.NAME] == (
            "Surfie"
        )

    def test_inactive_unit_dropped(self) -> None:
        """The empty second unit is dropped from the result."""

        assert set(ovpn.translate(_DATA)) == {1}

    def test_inactive_unit_state_only(self) -> None:
        """A non-active unit with state gets state but no settings."""

        data = {
            "VPNServer_enable": "1",
            "vpn_server_unit": "1",
            "vpn_server1_state": "2",
            "vpn_server2_state": "0",
            "vpn_server_port": "1194",
        }
        result = ovpn.translate(data)
        assert result[2] == {ARVpnServerField.STATE: ARVpnState.DISCONNECTED}
        assert ARVpnServerField.PORT not in result[2]

    def test_live_status_merged(self) -> None:
        """Connected status enriches the matching account."""

        data = dict(_DATA)
        data[ovpn.CLIENT_STATUS_KEY] = {
            "connected": [{"name": "Surfie", "vpn_ip": "10.8.0.2"}]
        }
        client = ovpn.translate(data)[1][ARVpnServerField.CLIENTS][0]
        assert client[ARVpnPeerField.STATE] is ARVpnState.CONNECTED


class TestIsLegacy:
    """Tests for _is_legacy firmware branching."""

    def test_none_identity(self) -> None:
        """No identity falls back to legacy services."""

        assert ovpn._is_legacy(None) is True

    def test_unknown_firmware(self) -> None:
        """Unknown firmware (non-stock) is legacy."""

        assert ovpn._is_legacy(_identity(ARFirmware())) is True

    def test_merlin_firmware(self) -> None:
        """Merlin-like firmware is legacy."""

        merlin = ARFirmware(
            major=(3, 0, 0, 4), minor=386, build=0, revision="beta"
        )
        assert ovpn._is_legacy(_identity(merlin)) is True

    def test_stock_below_388(self) -> None:
        """Stock firmware older than 388 is legacy."""

        old = ARFirmware(major=(3, 0, 0, 4), minor=384, build=0)
        assert ovpn._is_legacy(_identity(old)) is True

    def test_modern_stock(self) -> None:
        """Stock firmware 388 or newer is not legacy."""

        modern = ARFirmware(major=(3, 0, 0, 4), minor=388, build=0)
        assert ovpn._is_legacy(_identity(modern)) is False


class TestBuildTogglePayload:
    """Tests for build_toggle_payload."""

    def test_legacy_enable(self) -> None:
        """Legacy enable uses the per-unit start service."""

        services, arguments = ovpn.build_toggle_payload(2, True, None)
        assert services == ["start_vpnserver2"]
        assert arguments == {"id": 2}

    def test_legacy_disable(self) -> None:
        """Legacy disable uses the per-unit stop service."""

        services, arguments = ovpn.build_toggle_payload(1, False, None)
        assert services == ["stop_vpnserver1"]
        assert arguments == {"id": 1}

    def test_modern_enable(self) -> None:
        """Modern enable chains the service restarts and flags nvram on."""

        modern = _identity(ARFirmware(major=(3, 0, 0, 4), minor=388, build=0))
        services, arguments = ovpn.build_toggle_payload(1, True, modern)
        assert services == [
            ARService.OPENVPN_RESTART,
            ARService.CHPASS_RESTART,
            ARService.SAMBA_RESTART,
            ARService.DNS_RESTART,
        ]
        assert arguments == {"VPNServer_enable": 1, "id": 1}

    def test_modern_disable(self) -> None:
        """Modern disable stops the daemon and flags nvram off."""

        modern = _identity(ARFirmware(major=(3, 0, 0, 4), minor=388, build=0))
        services, arguments = ovpn.build_toggle_payload(1, False, modern)
        assert services == [
            ARService.OPENVPN_STOP,
            ARService.SAMBA_RESTART,
            ARService.DNS_RESTART,
        ]
        assert arguments == {"VPNServer_enable": 0, "id": 1}
