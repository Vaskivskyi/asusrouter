"""Tests for the clients translation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from asusrouter.modules.clients import translate
from asusrouter.modules.clients.model import ARClientConnection
from asusrouter.modules.clients.translate import build_clients
from asusrouter.modules.common.connection import ARConnectionType
from asusrouter.modules.common.device import ARDeviceType
from asusrouter.modules.common.internet import ARInternetMode
from asusrouter.modules.common.ip import ARIPMethod
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.wifi import ARWiFiAuth, ARWiFiBand, ARWiFiFrequency
from asusrouter.tools.identifiers import IpAddress, MacAddress

_ROUTER = "AA:BB:CC:00:00:01"
_C1 = "AA:BB:CC:00:00:11"
_C2 = "AA:BB:CC:00:00:12"
_NODE = "AA:BB:CC:00:00:2F"
_MIB = 1048576.0


def _identity() -> ARDeviceIdentity:
    """Identity whose MAC is the connected router."""

    identity = ARDeviceIdentity()
    identity._mac = MacAddress(_ROUTER)
    return identity


class TestHelpers:
    """Tests for the small translation helpers."""

    def test_clean_strips_trailing_space_keys(self) -> None:
        """Firmware trailing-space keys are normalized."""

        assert translate._clean({"conn_ts ": 1, "os_type ": 2}) == {
            "conn_ts": 1,
            "os_type": 2,
        }

    @pytest.mark.parametrize(
        ("value", "expected"),
        [("1", _MIB), ("0", 0.0), ("", None), (None, None)],
        ids=["one", "zero", "empty", "none"],
    )
    def test_rate(self, value: Any, expected: float | None) -> None:
        """Mibit/s link rate converts to bits/s, empty -> None."""

        assert translate._rate(value) == expected

    def test_since_ts(self) -> None:
        """Unix timestamp converts to a datetime; 0 -> None."""

        assert translate._since_ts("1700000000") == datetime(
            2023, 11, 14, 22, 13, 20, tzinfo=UTC
        )
        assert translate._since_ts("0") is None

    def test_since_delta(self) -> None:
        """A duration string yields a datetime; empty -> None."""

        assert isinstance(translate._since_delta("01:00:00"), datetime)
        assert translate._since_delta("") is None

    def test_name_precedence(self) -> None:
        """NickName wins over name; empty across entries -> None."""

        assert translate._name({"name": "n", "nickName": "nick"}) == "nick"
        assert translate._name({"name": "n"}, {"nickName": "x"}) == "x"
        assert translate._name({"name": ""}, {}) is None

    def test_is_mesh_node(self) -> None:
        """amesh_isRe marks a mesh node."""

        assert translate._is_mesh_node({"amesh_isRe": "1"}) is True
        assert translate._is_mesh_node({"amesh_isRe": "0"}) is False
        assert translate._is_mesh_node({}) is False

    @pytest.mark.parametrize(
        ("tag", "expected"),
        [
            ("5G", ARWiFiBand.BAND_5G1),
            ("5G1", ARWiFiBand.BAND_5G1),
            ("5G2", ARWiFiBand.BAND_5G2),
            ("6G1", ARWiFiBand.BAND_6G1),
            ("2G", ARWiFiBand.BAND_2G1),
            ("7G1", None),
            ("bad", None),
        ],
        ids=["5g", "5g1", "5g2", "6g1", "2g", "unknown_freq", "no_match"],
    )
    def test_tag_to_band(self, tag: str, expected: Any) -> None:
        """Band tags are 1-based; bare == first; junk -> None."""

        assert translate._tag_to_band(tag) is expected


class TestBuildClients:
    """Tests for build_clients."""

    def test_non_dict(self) -> None:
        """A non-dict payload yields no clients."""

        assert build_clients(None, _identity()) == {}

    def test_skips_non_client_keys_and_bad_macs(self) -> None:
        """Maclist / ClientAPILevel / invalid entries are skipped."""

        raw = {
            "get_clientlist": {
                "maclist": ["x"],
                "ClientAPILevel": "7",
                "not-a-mac": {"mac": "not-a-mac"},
                "bad": "not-a-dict",
            }
        }

        assert build_clients(raw, _identity()) == {}

    def test_excludes_mesh_node_and_router(self) -> None:
        """Mesh nodes and the router itself are not clients."""

        raw = {
            "get_clientlist": {
                _NODE: {"mac": _NODE, "amesh_isRe": "1", "isOnline": "1"},
                _ROUTER: {"mac": _ROUTER, "isOnline": "1"},
                _C1: {"mac": _C1, "isOnline": "1", "isWL": "0"},
            }
        }

        result = build_clients(raw, _identity())

        assert list(result) == [MacAddress(_C1)]

    def test_db_only_client_is_offline(self) -> None:
        """A database-only MAC becomes an offline, connection-less client."""

        raw = {
            "get_clientlist_from_json_database": {
                _C2: {
                    "mac": _C2,
                    "name": "Old",
                    "vendor": "Acme",
                    "os_type": "3",
                    "amesh_isRe": "0",
                }
            }
        }

        client = build_clients(raw, _identity())[MacAddress(_C2)]

        assert client.online is False
        assert client.connection is None
        assert client.name == "Old"
        assert client.os_type == 3
        assert client.device_type is ARDeviceType.UNKNOWN

    def test_db_only_mesh_node_excluded(self) -> None:
        """A database-only mesh node is excluded too."""

        raw = {
            "get_clientlist_from_json_database": {
                _NODE: {"mac": _NODE, "amesh_isRe": "1"},
            }
        }

        assert build_clients(raw, _identity()) == {}

    def test_online_wireless_client_with_db_merge(self) -> None:
        """Online wireless client merges DB extras into the model."""

        raw = {
            "get_clientlist": {
                _C1: {
                    "mac": _C1,
                    "isOnline": "1",
                    "isWL": "2",
                    "rssi": "-46",
                    "curRx": "1",
                    "curTx": "0",
                    "ip": "192.168.1.5",
                    "ipMethod": "DHCP",
                    "internetState": "1",
                    "internetMode": "allow",
                    "amesh_papMac": _NODE,
                    "ssid": "Net",
                    "wlAuth": "WPA2-PSK",
                    "isGN": "",
                    "sdn_type": "MAINFH",
                    "mlo": "0",
                    "name": "PC",
                    "nickName": "MyPC",
                    "vendor": "Apple, Inc.",
                    "type": "5",
                }
            },
            "get_clientlist_from_json_database": {
                _C1: {
                    "mac": _C1,
                    "vendorclass": "Apple",
                    "os_type": "2",
                    "conn_ts": "1700000000",
                }
            },
        }

        client = build_clients(raw, _identity())[MacAddress(_C1)]

        assert client.online is True
        assert client.name == "MyPC"
        assert client.vendor == "Apple, Inc."
        assert client.vendor_class == "Apple"
        assert client.device_type is ARDeviceType.IP_CAM
        assert client.os_type == 2
        assert client.internet_mode is ARInternetMode.ALLOW

        conn = client.connection
        assert conn is not None
        assert conn.type is ARConnectionType.WIRELESS
        assert conn.ip == IpAddress("192.168.1.5")
        assert conn.ip_method is ARIPMethod.DHCP
        assert conn.internet_access is True
        assert conn.node == MacAddress(_NODE)
        assert conn.ssid == "Net"
        assert conn.security is ARWiFiAuth.WPA2_PSK
        assert conn.guest is False
        assert conn.mlo is False
        assert conn.connected_since == datetime(
            2023, 11, 14, 22, 13, 20, tzinfo=UTC
        )
        assert len(conn.links) == 1
        link = conn.links[0]
        assert link.frequency is ARWiFiFrequency.FREQ_5G
        assert link.rssi == -46
        assert link.rx_speed == _MIB
        assert link.tx_speed == 0.0


class TestConnection:
    """Tests for connection-specific behavior."""

    def _online(self, **extra: Any) -> ARClientConnection:
        raw = {"get_clientlist": {_C1: {"mac": _C1, "isOnline": "1", **extra}}}
        conn = build_clients(raw, _identity())[MacAddress(_C1)].connection
        assert conn is not None
        return conn

    def test_wired_has_no_links(self) -> None:
        """A wired client has WIRED type and no links."""

        conn = self._online(isWL="0", amesh_papMac="")

        assert conn.type is ARConnectionType.WIRED
        assert conn.links == []
        assert conn.mlo is False
        # empty papMac falls back to the router
        assert conn.node == MacAddress(_ROUTER)

    def test_guest_detection(self) -> None:
        """IsGN set with a non-main SDN type marks a guest."""

        assert (
            self._online(isWL="1", isGN="2", sdn_type="LEGACY").guest is True
        )
        assert (
            self._online(isWL="1", isGN="2", sdn_type="MAINFH").guest is False
        )

    def test_security_absent(self) -> None:
        """No wlAuth leaves security unset."""

        assert self._online(isWL="1").security is None

    def test_dualband_iswl_3_is_5g(self) -> None:
        """IsWL == 3 normalizes to 5G."""

        conn = self._online(isWL="3")

        assert conn.links[0].frequency is ARWiFiFrequency.FREQ_5G

    def test_unknown_iswl_no_links(self) -> None:
        """An unmappable isWL yields no links."""

        conn = self._online(isWL="9")

        assert conn.links == []


class TestMLO:
    """Tests for multi-link (MLO) building."""

    def test_live_mlo_links(self) -> None:
        """Live mlo_links become one link per radio with metrics."""

        conn = build_clients(
            {
                "get_clientlist": {
                    _C1: {
                        "mac": _C1,
                        "isOnline": "1",
                        "isWL": "2",
                        "mlo": "1",
                        "mlo_links": {
                            "5G1": {
                                "mac": _C2,
                                "rssi": "-63",
                                "tx": "1",
                                "rx": "0",
                                "conn_time": "01:00:00",
                            },
                            "7G": {"mac": _C2, "rssi": "-70"},
                            "bad": "not-a-dict",
                        },
                    }
                }
            },
            _identity(),
        )[MacAddress(_C1)].connection

        assert conn is not None
        assert conn.mlo is True
        assert len(conn.links) == 2
        link = conn.links[0]
        assert link.band is ARWiFiBand.BAND_5G1
        assert link.frequency is ARWiFiFrequency.FREQ_5G
        assert link.mac == MacAddress(_C2)
        assert link.rssi == -63
        assert link.tx_speed == _MIB
        assert isinstance(link.connected_since, datetime)
        # Unmapped radio -> no band, unknown frequency
        assert conn.links[1].band is None
        assert conn.links[1].frequency is ARWiFiFrequency.UNKNOWN

    def test_offline_mlo_from_db_macs(self) -> None:
        """MLO without live links uses DB per-band MACs; junk is skipped."""

        raw = {
            "get_clientlist": {
                _C1: {"mac": _C1, "isOnline": "1", "isWL": "2", "mlo": "1"}
            },
            "get_clientlist_from_json_database": {
                _C1: {
                    "mac": _C1,
                    "mlo": "1",
                    "mlo_5G_mac": _C2,  # -> BAND_5G1
                    "mlo_5G2_mac": _NODE,  # -> BAND_5G2
                    "mlo_7G_mac": _C2,  # unmappable band -> skipped
                    "mlo_all_mac": f"<{_C2}",  # combined -> skipped
                    "vendor": "x",  # non-mlo field -> skipped
                }
            },
        }

        conn = build_clients(raw, _identity())[MacAddress(_C1)].connection

        assert conn is not None
        assert conn.mlo is True
        bands = {link.band for link in conn.links}
        assert bands == {ARWiFiBand.BAND_5G1, ARWiFiBand.BAND_5G2}

    def test_mlo_flagged_but_no_data_falls_back(self) -> None:
        """MLO flagged with no links/macs falls back to a single link."""

        conn = build_clients(
            {
                "get_clientlist": {
                    _C1: {
                        "mac": _C1,
                        "isOnline": "1",
                        "isWL": "1",
                        "mlo": "1",
                    }
                }
            },
            _identity(),
        )[MacAddress(_C1)].connection

        assert conn is not None
        assert len(conn.links) == 1
        assert conn.links[0].frequency is ARWiFiFrequency.FREQ_2G
