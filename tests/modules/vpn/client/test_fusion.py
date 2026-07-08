"""Tests for the VPN Fusion client backend."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.vpn.client import fusion
from asusrouter.modules.vpn.enums import (
    ARVpnClientField,
    ARVpnProtocol,
    ARVpnState,
)
from asusrouter.tools.identifiers import IpAddress, IpInterface, Password

# Three profiles (fake identifiers): a connected WireGuard client, a connecting
# OpenVPN client on the default WAN, and a failed, inactive PPTP client
_DATA: dict[str, Any] = {
    # The device HTML-encodes the `<` / `>` list delimiters (&#60 / &#62)
    "get_vpnc_status": "2&#620&#625&#601&#620&#626&#604&#622&#627",
    "get_vpnc_nondef_wan_prof_list": "5&#620&#606&#621&#607&#620",
    "vpnc_default_wan": "6",
    "vpnc_pptp_options_x_list": "&#60auto&#60auto&#60dhcp",
    "vpnc_clientlist": (
        "Home/WG&#62WireGuard&#622&#62&#62&#621&#625&#62&#62&#620&#620&#62Web"
        "&#60OVPN&#62OpenVPN&#623&#62user1&#62pass1&#621&#626"
        "&#62region1&#62&#620&#620&#62Web"
        "&#60MyPPTP&#62PPTP&#62vpn.example.test&#62puser&#62ppass"
        "&#620&#627&#62&#62&#620&#620&#62Web"
    ),
    "wgc2_priv": "cHJpdmZha2U=",
    "wgc2_addr": "10.9.0.2/32",
    "wgc2_dns": "10.9.0.1",
    "wgc2_mtu": "1420",
    "wgc2_ppub": "cHViZmFrZQ==",
    "wgc2_psk": "",
    "wgc2_aips": "0.0.0.0/0",
    "wgc2_ep_addr": "203.0.113.5",
    "wgc2_ep_port": "51820",
    "wgc2_alive": "25",
    "wgc2_nat": "1",
}


class TestNvramKeys:
    """Tests for nvram_keys."""

    def test_contains(self) -> None:
        """Keys cover the clientlist plus every WireGuard client unit."""

        keys = fusion.nvram_keys()
        assert "vpnc_clientlist" in keys
        assert "vpnc_default_wan" in keys
        assert "wgc1_priv" in keys
        assert f"wgc{fusion.WG_UNITS[-1]}_nat" in keys


class TestStatus:
    """Tests for _status."""

    def test_maps_by_vpnc_idx(self) -> None:
        """Each status row maps vpnc_idx to (state, reason)."""

        status = fusion._status(_DATA)
        assert status[5] == (ARVpnState.CONNECTED, 0)
        assert status[6] == (ARVpnState.CONNECTING, 0)
        assert status[7] == (ARVpnState.ERROR, 2)

    def test_skips_bad_rows(self) -> None:
        """Rows without a vpnc_idx are skipped; unknown codes are UNKNOWN."""

        status = fusion._status({"get_vpnc_status": "2>0><9>0>3"})
        assert 3 in status
        assert status[3][0] is ARVpnState.UNKNOWN
        assert len(status) == 1

    def test_absent(self) -> None:
        """No status hook yields an empty map."""

        assert fusion._status({}) == {}


class TestDefaultWanSupport:
    """Tests for _default_wan_support."""

    def test_maps(self) -> None:
        """`0` means allowed on the default WAN; anything else is not."""

        support = fusion._default_wan_support(_DATA)
        assert support == {5: True, 6: False, 7: True}

    def test_absent(self) -> None:
        """No hook yields an empty map."""

        assert fusion._default_wan_support({}) == {}

    def test_skips_bad_rows(self) -> None:
        """Rows without a numeric vpnc_idx are skipped."""

        support = fusion._default_wan_support(
            {"get_vpnc_nondef_wan_prof_list": ">0<5>0"}
        )
        assert support == {5: True}


class TestWireguard:
    """Tests for _wireguard."""

    def test_reads_unit(self) -> None:
        """The `wgc{unit}_*` config maps to typed fields; empty psk absent."""

        fields = fusion._wireguard(_DATA, 2)
        assert isinstance(fields[ARVpnClientField.PRIVATE_KEY], Password)
        assert fields[ARVpnClientField.ADDRESS] == IpInterface("10.9.0.2/32")
        assert fields[ARVpnClientField.DNS] == IpAddress("10.9.0.1")
        assert fields[ARVpnClientField.ENDPOINT_ADDRESS] == IpAddress(
            "203.0.113.5"
        )
        assert fields[ARVpnClientField.ENDPOINT_PORT] == 51820
        assert fields[ARVpnClientField.NAT] is True
        assert ARVpnClientField.PSK not in fields

    def test_empty_unit(self) -> None:
        """An absent unit yields no fields."""

        assert fusion._wireguard(_DATA, 4) == {}


class TestTranslate:
    """Tests for translate."""

    def test_empty(self) -> None:
        """No clientlist yields an empty result."""

        assert fusion.translate({}) == {}

    def test_groups_by_protocol(self) -> None:
        """Profiles group by protocol, keyed by vpnc_idx."""

        result = fusion.translate(_DATA)
        assert set(result) == {
            ARVpnProtocol.WIREGUARD,
            ARVpnProtocol.OPENVPN,
            ARVpnProtocol.PPTP,
        }
        assert set(result[ARVpnProtocol.WIREGUARD]) == {5}

    def test_wireguard_profile(self) -> None:
        """The WireGuard profile carries three ids, status and peer config."""

        wg = fusion.translate(_DATA)[ARVpnProtocol.WIREGUARD][5]
        assert wg[ARVpnClientField.NAME] == "Home/WG"
        assert wg[ARVpnClientField.UNIT] == 0  # position / control unit
        assert wg[ARVpnClientField.SERVER] == 2  # per-protocol unit
        assert wg[ARVpnClientField.VPNC_INDEX] == 5  # status key
        assert wg[ARVpnClientField.ENABLED] is True
        assert wg[ARVpnClientField.STATE] is ARVpnState.CONNECTED
        assert wg[ARVpnClientField.DEFAULT_WAN_SUPPORT] is True
        assert wg[ARVpnClientField.DEFAULT_WAN] is False
        assert wg[ARVpnClientField.ALLOWED_IPS] == [IpInterface("0.0.0.0/0")]
        assert ARVpnClientField.STATE_REASON not in wg  # connected, no reason

    def test_openvpn_profile(self) -> None:
        """The OpenVPN profile carries clientlist auth and default WAN."""

        ovpn = fusion.translate(_DATA)[ARVpnProtocol.OPENVPN][6]
        assert ovpn[ARVpnClientField.SERVER] == 3
        assert ovpn[ARVpnClientField.USERNAME] == "user1"
        assert isinstance(ovpn[ARVpnClientField.PASSWORD], Password)
        assert ovpn[ARVpnClientField.REGION] == "region1"
        assert ovpn[ARVpnClientField.STATE] is ARVpnState.CONNECTING
        assert ovpn[ARVpnClientField.DEFAULT_WAN] is True
        assert ovpn[ARVpnClientField.DEFAULT_WAN_SUPPORT] is False
        # OpenVPN keeps no wgc peer config
        assert ARVpnClientField.PRIVATE_KEY not in ovpn

    def test_pptp_profile(self) -> None:
        """PPTP keeps a host server, custom options, error state and reason."""

        pptp = fusion.translate(_DATA)[ARVpnProtocol.PPTP][7]
        assert pptp[ARVpnClientField.SERVER] == "vpn.example.test"
        assert pptp[ARVpnClientField.ENABLED] is False
        assert pptp[ARVpnClientField.PPTP_OPTIONS] == "dhcp"
        assert pptp[ARVpnClientField.STATE] is ARVpnState.ERROR
        assert pptp[ARVpnClientField.STATE_REASON] == 2

    def test_skips_empty_rows(self) -> None:
        """Empty clientlist rows are skipped without advancing protocols."""

        data = dict(_DATA)
        data["vpnc_clientlist"] = "<OVPN>OpenVPN>3>u>p>1>6>>>0>0>Web<"
        result = fusion.translate(data)
        assert set(result) == {ARVpnProtocol.OPENVPN}

    def test_skips_nameless_row(self) -> None:
        """A row with an empty name is dropped."""

        data = dict(_DATA)
        data["vpnc_clientlist"] = ">OpenVPN>3>u>p>1>6>>>0>0>Web"
        assert fusion.translate(data) == {}


class TestBuildTogglePayload:
    """Tests for build_toggle_payload."""

    def test_skips_leading_empty_row(self) -> None:
        """A leading empty clientlist row is skipped when locating the unit."""

        clientlist = "<Prtn>OpenVPN>4>u>p>0>6>>>0>0>Web"
        services, arguments = fusion.build_toggle_payload(
            clientlist, ARVpnProtocol.OPENVPN, 4, True
        )
        assert arguments["vpnc_unit"] == 0
        assert ">1>6>" in arguments["vpnc_clientlist"]

    def test_missing_unit(self) -> None:
        """A protocol/unit not in the clientlist yields None."""

        assert (
            fusion.build_toggle_payload(
                "A>OpenVPN>1>>>0>2>", ARVpnProtocol.WIREGUARD, 1, True
            )
            is None
        )
