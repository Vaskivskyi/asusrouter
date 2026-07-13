"""Tests for the AiMesh topology parsing."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.aimesh.capability import ARAiMeshFeature
from asusrouter.modules.aimesh.topology import (
    ARAiMeshBackhaul,
    ARAiMeshMedium,
    ARAiMeshNode,
    ARAiMeshRole,
    ARAiMeshTopology,
    ARAiMeshVif,
    _config_flag,
    _dwb_band,
    _parse_vif_prefix,
    _preferred_parent,
    _translate_backhaul,
    _translate_band_units,
    _translate_node,
    _translate_ports,
    _translate_vifs,
    _wired_link_rate,
    translate_onboarding_status,
    translate_topology,
)
from asusrouter.modules.common.region import ARRegion
from asusrouter.modules.firmware import ARFirmware
from asusrouter.modules.ports.enums import ARPortSpeed
from asusrouter.modules.wifi import ARWiFiBand
from asusrouter.tools.identifiers import MacAddress

_ROOT = "AA:00:00:00:00:00"
_WIRED = "BB:00:00:00:00:00"
_WL = "CC:00:00:00:00:00"
_AP5G = "AA:00:00:00:00:14"


def _root_raw() -> dict[str, Any]:
    """Build a root (CAP) node."""

    return {
        "mac": _ROOT,
        "alias": "Root",
        "model_name": "M1",
        "ui_model_name": "M1 UI",
        "product_id": "P1",
        "icon_model_name": "ICON1",
        "tcode": "US/01",
        "ip": "192.168.1.1",
        "fwver": "fw1",
        "newfwver": "fw2",
        "online": "1",
        "level": "0",
        "re_path": "0",
        "ap2g": "AA:00:00:00:00:10",
        "ap2g_fh": "AA:00:00:00:00:11",
        "ap2g_iot_fh": "AA:00:00:00:00:12",
        "ap2g_ssid": "S2",
        "ap2g_ssid_fh": "S2FH",
        "ap5g": _AP5G,
        "ap5g_fh": "AA:00:00:00:00:15",
        "ap6g": "AA:00:00:00:00:18",
        "apdwb": "AA:00:00:00:00:18",
        "dwb_band": "2",
        "band_info": {"0": {"unit": 0}, "1": {"unit": 1}, "4": {"unit": 2}},
        "wired_mac": [_WIRED],
        "capability": {
            "1": 95,
            "2": "1",
            "9": "1",
            "26": {
                "wifi_band": {
                    "band1": {
                        "band": "1",
                        "count": "2",
                        "vif": {
                            "wl0.1": {"type": "1", "prefix": "wl0.1"},
                            "wl0.4": {"type": "8", "prefix": "wl0.4"},
                        },
                    }
                }
            },
            "27": {
                "lan_port": {
                    "lan1": {
                        "label_name": "L1",
                        "max_rate": "2500",
                        "index": "1",
                    }
                }
            },
            "28": {
                "wan_port": {"wan1": {"label_name": "W0", "max_rate": "10000"}}
            },
        },
        "plc_status": {},
        "moca_status": {},
        "mlo_status": {"msta": "X"},
        "config": {"ctrl_led": {"led_val": "1"}},
    }


def _wl_raw() -> dict[str, Any]:
    """Build a wireless 5G-2 backhaul node."""

    return {
        "mac": _WL,
        "alias": "WL",
        "ui_model_name": "M2",
        "model_name": "M2_RAW",
        "product_id": "P2",
        "tcode": "EU/01",
        "online": "1",
        "level": "1",
        "re_path": "8",
        "band_num": "3",
        "ap2g": "CC:00:00:00:00:10",
        "ap5g": "CC:00:00:00:00:14",
        "ap5g1": "CC:00:00:00:00:18",
        "apdwb": "CC:00:00:00:00:18",
        "dwb_band": "2",
        "band_info": {"0": {"unit": 0}, "2": {"unit": 1}, "3": {"unit": 2}},
        "pap5g": _AP5G,
        "pap5g_ssid": "PARENT_SSID",
        "rssi5g": "-54",
        "sta5g": "CC:00:00:00:00:1A",
        "ap5g_ssid_fh": "FH5",
        "config": {
            "wireless": {"wl0_radio": "1", "wl1_radio": "1", "wl2_radio": "0"},
            "link_aggregation": {"lacp_enabled": "0"},
            "ctrl_led": {"led_val": "0"},
            "prefer_ap": {"amas_wlc_target_bssid": f"<{_ROOT}"},
        },
    }


def _wired_raw() -> dict[str, Any]:
    """Build a wired backhaul node."""

    return {
        "mac": _WIRED,
        "alias": "WIRED",
        "ui_model_name": "M3",
        "online": "1",
        "level": "0",
        "re_path": "1",
        "ap2g": "",
        "ap5g": "",
        "sta2g": "BB:00:00:00:00:91",
        "sta5g": "BB:00:00:00:00:94",
        "band_info": {"0": {"unit": 0}, "1": {"unit": 1}},
        "wired_port": {"wan_port": {"WAN 0": {"link_rate": "G"}}},
        "config": {"wireless": {"wl0_radio": "0", "wl1_radio": "0"}},
    }


class TestParseTopology:
    """Tests for translate_topology and the resulting graph."""

    def test_three_nodes(self) -> None:
        """The sample mesh resolves to root + two children."""

        topo = translate_topology([_root_raw(), _wl_raw(), _wired_raw()])

        assert len(topo.nodes) == 3
        root = topo.root()
        assert root is not None
        assert root.role is ARAiMeshRole.ROUTER
        assert root.backhaul is None

    def test_wireless_backhaul(self) -> None:
        """The wireless node resolves to a 5G-2 uplink to the root."""

        topo = translate_topology([_root_raw(), _wl_raw()])
        node = topo.get(_WL)

        assert node is not None
        bh = node.backhaul
        assert bh is not None
        assert bh.medium is ARAiMeshMedium.WIRELESS
        assert bh.band is ARWiFiBand.BAND_5G2
        assert bh.mac_parent == MacAddress(_ROOT)
        assert bh.rssi == -54
        assert bh.mac_sta == MacAddress("CC:00:00:00:00:1A")

    def test_wired_backhaul(self) -> None:
        """The wired node resolves via the parent's wired_mac list."""

        topo = translate_topology([_root_raw(), _wired_raw()])
        bh = topo.get(_WIRED).backhaul

        assert bh.medium is ARAiMeshMedium.WIRED
        assert bh.mac_parent == MacAddress(_ROOT)
        assert bh.mac_sta == MacAddress(_WIRED)
        assert bh.port == 1

    def test_root_radios_and_ports(self) -> None:
        """The root radios carry MACs, units, dwb and ports."""

        root = translate_topology([_root_raw()]).get(_ROOT)

        assert set(root.radios) == {
            ARWiFiBand.BAND_2G1,
            ARWiFiBand.BAND_5G1,
            ARWiFiBand.BAND_6G1,
        }
        r2 = root.radios[ARWiFiBand.BAND_2G1]
        assert r2.unit == 0
        assert r2.ssid == "S2"
        assert r2.mac_iot == MacAddress("AA:00:00:00:00:12")
        assert root.radios[ARWiFiBand.BAND_6G1].dwb is True
        assert len(root.ports) == 2
        assert any(p.is_wan and p.max_rate == 10000 for p in root.ports)

    def test_radio_on_from_config(self) -> None:
        """radio_on reflects the per-unit wireless config."""

        node = translate_topology([_wl_raw()]).get(_WL)

        assert node.radios[ARWiFiBand.BAND_5G1].state is True
        assert node.radios[ARWiFiBand.BAND_5G2].state is False

    def test_radios_off_still_present(self) -> None:
        """Radios listed in band_info are present even when off."""

        radios = translate_topology([_wired_raw()]).get(_WIRED).radios

        assert set(radios) == {ARWiFiBand.BAND_2G1, ARWiFiBand.BAND_5G1}
        radio = radios[ARWiFiBand.BAND_2G1]
        assert radio.mac_ap is None
        assert radio.state is False

    def test_radio_sta_mac(self) -> None:
        """Each radio carries its station MAC (even when off)."""

        radios = translate_topology([_wired_raw()]).get(_WIRED).radios

        assert radios[ARWiFiBand.BAND_2G1].mac_sta == MacAddress(
            "BB:00:00:00:00:91"
        )
        assert radios[ARWiFiBand.BAND_5G1].mac_sta == MacAddress(
            "BB:00:00:00:00:94"
        )

    def test_radio_sta_shared_per_frequency(self) -> None:
        """Both 5G radios share the single 5G station MAC."""

        radios = translate_topology([_wl_raw()]).get(_WL).radios
        sta = MacAddress("CC:00:00:00:00:1A")

        assert radios[ARWiFiBand.BAND_5G1].mac_sta == sta
        assert radios[ARWiFiBand.BAND_5G2].mac_sta == sta

    def test_raw_status_dicts_preserved(self) -> None:
        """plc/moca/mlo status dicts are stored raw (even empty)."""

        node = translate_topology([_root_raw()]).get(_ROOT)

        assert node.plc_status == {}
        assert node.moca_status == {}
        assert node.mlo_status == {"msta": "X"}


class TestOnboardingStatus:
    """Tests for the onboarding status + topology wiring."""

    def test_translate(self) -> None:
        """Onboarding status fields decode to ints/bool."""

        status = translate_onboarding_status(
            {
                "cfg_ready": "1",
                "cfg_re_maxnum": "16",
                "cfg_recount": "2",
                "cfg_obrssi": "-20",
                "cfg_wifi_quality": "-65",
                "cfg_ui_obmodel": "RT-AX88U",
            }
        )

        assert status.ready is True
        assert status.re_maxnum == 16
        assert status.re_count == 2
        assert status.rssi == -20
        assert status.wifi_quality == -65
        assert status.model == "RT-AX88U"

    def test_translate_empty(self) -> None:
        """Non-dict input yields a default status."""

        status = translate_onboarding_status("x")

        assert status.ready is False
        assert status.re_maxnum is None

    def test_topology_carries_status_and_onboarding(self) -> None:
        """translate_topology attaches status and raw onboarding."""

        status = translate_onboarding_status({"cfg_ready": "1"})
        topo = translate_topology([], status=status, onboarding={"a": 1})

        assert topo.status.ready is True
        assert topo.onboarding == {"a": 1}

    def test_topology_defaults(self) -> None:
        """Without args the status is default and onboarding is None."""

        topo = translate_topology([])

        assert topo.status.ready is False
        assert topo.onboarding is None

    @pytest.mark.parametrize(
        "data", [None, "x", 5, {}], ids=["none", "str", "int", "dict"]
    )
    def test_unusable_input(self, data: Any) -> None:
        """Non-list input yields an empty topology."""

        assert translate_topology(data).nodes == {}

    def test_skips_non_dict_and_macless(self) -> None:
        """Non-dict entries and nodes without a MAC are skipped."""

        topo = translate_topology(["x", {"alias": "no-mac"}, _root_raw()])

        assert list(topo.nodes) == [MacAddress(_ROOT)]


class TestTopologyHelpers:
    """Tests for the ARAiMeshTopology reconstruction helpers."""

    def _topo(self) -> ARAiMeshTopology:
        return translate_topology([_root_raw(), _wl_raw(), _wired_raw()])

    def test_get_and_macs(self) -> None:
        """Get resolves a node; macs lists all."""

        topo = self._topo()
        assert topo.get(_ROOT).mac == MacAddress(_ROOT)
        assert topo.get("bad") is None
        assert len(topo.macs()) == 3

    def test_parent_and_children(self) -> None:
        """Parent/children resolve across the star."""

        topo = self._topo()
        assert topo.parent(_WL).mac == MacAddress(_ROOT)
        assert {c.mac for c in topo.children(_ROOT)} == {
            MacAddress(_WL),
            MacAddress(_WIRED),
        }

    def test_parent_edge_cases(self) -> None:
        """Parent is None for root and unknown nodes."""

        topo = self._topo()
        assert topo.parent(_ROOT) is None
        assert topo.parent("bad") is None
        assert topo.children("bad") == []

    def test_descendants_and_path(self) -> None:
        """Descendants gather the subtree; path climbs to root."""

        topo = self._topo()
        assert {d.mac for d in topo.descendants(_ROOT)} == {
            MacAddress(_WL),
            MacAddress(_WIRED),
        }
        assert [n.mac for n in topo.path_to_root(_WL)] == [
            MacAddress(_WL),
            MacAddress(_ROOT),
        ]

    def test_root_absent(self) -> None:
        """A mesh without a router returns no root."""

        assert ARAiMeshTopology().root() is None


class TestBackhaulBranches:
    """Targeted tests for the backhaul medium/band branches."""

    def test_2g(self) -> None:
        """re_path 2 resolves to a 2.4G uplink."""

        raw = {"mac": _WL, "re_path": "2", "pap2g": "P", "sta2g": _WL}
        bh = _translate_backhaul(raw, 2, [{"mac": _ROOT, "ap2g": "P"}])
        assert bh.band is ARWiFiBand.BAND_2G1
        assert bh.mac_parent == MacAddress(_ROOT)

    def test_6g(self) -> None:
        """re_path 128 resolves to a 6G uplink via ap6g1."""

        raw = {"mac": _WL, "re_path": "128", "pap6g": "P", "sta6g": _WL}
        bh = _translate_backhaul(raw, 128, [{"mac": _ROOT, "ap6g1": "P"}])
        assert bh.band is ARWiFiBand.BAND_6G1

    def test_5g_primary(self) -> None:
        """re_path 8 without tri-band stays primary 5G."""

        bh = _translate_backhaul({"mac": _WL, "re_path": "8"}, 8, [])
        assert bh.band is ARWiFiBand.BAND_5G1

    def test_mlo(self) -> None:
        """re_path 512 resolves an MLO uplink."""

        raw = {"mac": _WL, "papmlo": _ROOT, "mlo_status": {"msta": _WL}}
        bh = _translate_backhaul(raw, 512, [])
        assert bh.medium is ARAiMeshMedium.MLO
        assert bh.mac_parent == MacAddress(_ROOT)
        assert bh.mac_sta == MacAddress(_WL)

    @pytest.mark.parametrize(
        ("field", "medium"),
        [
            ("plc_status", ARAiMeshMedium.PLC),
            ("moca_status", ARAiMeshMedium.MOCA),
        ],
    )
    def test_wired_medium(self, field: str, medium: ARAiMeshMedium) -> None:
        """Powerline/MoCA refine the wired medium."""

        bh = _translate_backhaul({"mac": _WIRED, field: {"x": 1}}, 1, [])
        assert bh.medium is medium

    def test_unknown_re_path(self) -> None:
        """An unknown re_path yields no backhaul."""

        assert _translate_backhaul({"mac": _WL}, 999, []) is None

    def test_parent_not_found(self) -> None:
        """No matching parent leaves parent None."""

        bh = _translate_backhaul(
            {"mac": _WL, "re_path": "2", "pap2g": "P"}, 2, []
        )
        assert bh.mac_parent is None
        bh_wired = _translate_backhaul({"mac": _WL}, 1, [])
        assert bh_wired.mac_parent is None

    def test_wireless_parent_empty_pap(self) -> None:
        """An empty pap leaves the wireless parent None."""

        bh = _translate_backhaul(
            {"mac": _WL, "re_path": "2", "pap2g": ""}, 2, []
        )
        assert bh.mac_parent is None


class TestSmallHelpers:
    """Tests for band-unit and port helpers and _translate_node."""

    @pytest.mark.parametrize(
        ("band_info", "expected"),
        [
            ("x", {}),
            ({"0": {"unit": 0}, "9": {"unit": 5}}, {"2g": 0}),
            ({"0": "x"}, {}),
            ({"0": {"unit": "bad"}}, {}),
        ],
        ids=["not_dict", "known_unknown_index", "info_not_dict", "no_unit"],
    )
    def test_band_units(
        self, band_info: Any, expected: dict[str, int]
    ) -> None:
        """band_info decodes to AP-suffix -> unit."""

        assert _translate_band_units({"band_info": band_info}) == expected

    @pytest.mark.parametrize(
        "capability",
        [
            "x",
            {},
            {"27": "x"},
            {"27": {"lan_port": "x"}},
            {"27": {"lan_port": {"l": "x"}}},
        ],
        ids=[
            "not_dict",
            "empty",
            "section_not_dict",
            "group_not_dict",
            "info_not_dict",
        ],
    )
    def test_ports_empty(self, capability: Any) -> None:
        """Malformed capability yields no ports."""

        assert _translate_ports({"capability": capability}) == []

    def test_node_requires_mac(self) -> None:
        """A node without a MAC is dropped."""

        assert _translate_node({"alias": "x"}, []) is None

    def test_node_dataclasses(self) -> None:
        """Dataclasses are constructible and typed."""

        node = ARAiMeshNode(mac=MacAddress(_ROOT))
        assert isinstance(node.backhaul, type(None))
        assert isinstance(node.firmware, ARFirmware)
        bh = ARAiMeshBackhaul(medium=ARAiMeshMedium.WIRED)
        assert bh.band is None


class TestTypedFields:
    """Tests for the strongly-typed node fields."""

    def test_alias_mac_is_wrapped(self) -> None:
        """An alias that is a MAC becomes a MacAddress."""

        raw = _root_raw()
        raw["alias"] = "AA:00:00:00:00:99"

        alias = translate_topology([raw]).get(_ROOT).alias

        assert isinstance(alias, MacAddress)
        assert alias == MacAddress("AA:00:00:00:00:99")

    def test_alias_plain_string(self) -> None:
        """A non-MAC alias stays a plain string."""

        alias = translate_topology([_root_raw()]).get(_ROOT).alias

        assert alias == "Root"
        assert not isinstance(alias, MacAddress)

    def test_alias_absent(self) -> None:
        """A missing alias is None."""

        raw = _root_raw()
        del raw["alias"]

        assert translate_topology([raw]).get(_ROOT).alias is None

    def test_firmware_typed(self) -> None:
        """Firmware fields are parsed into ARFirmware."""

        node = translate_topology([_root_raw()]).get(_ROOT)

        assert isinstance(node.firmware, ARFirmware)
        assert isinstance(node.firmware_available, ARFirmware)

    def test_firmware_update_true(self) -> None:
        """firmware_update is set when a newer version is available."""

        raw = _root_raw()
        raw["fwver"] = "3.0.0.6.102_40456"
        raw["newfwver"] = "3.0.0.6.102_40537"

        assert translate_topology([raw]).get(_ROOT).firmware_update is True

    def test_firmware_update_false_on_invalid(self) -> None:
        """Unparseable versions yield no update."""

        # _root_raw has fwver/newfwver `fw1`/`fw2` (not valid versions)
        assert (
            translate_topology([_root_raw()]).get(_ROOT).firmware_update
            is False
        )

    def test_port_speed_typed(self) -> None:
        """Port max_rate is an ARPortSpeed member."""

        ports = translate_topology([_root_raw()]).get(_ROOT).ports
        wan = next(p for p in ports if p.is_wan)

        assert wan.max_rate is ARPortSpeed.MBPS_10000


class TestEnrichedFields:
    """Tests for the extended node/radio/backhaul fields."""

    def test_model_fields(self) -> None:
        """Model maps product_id/model_name/ui_model_name + icon."""

        node = translate_topology([_root_raw()]).get(_ROOT)

        assert node.model == "P1"
        assert node.model_original == "M1"
        assert node.model_display == "M1 UI"
        assert node.icon == "ICON1"

    def test_region(self) -> None:
        """Tcode resolves to region + area."""

        node = translate_topology([_root_raw()]).get(_ROOT)

        assert node.region is ARRegion.US
        assert node.region_area == 1

    def test_led_and_dwb(self) -> None:
        """Led decodes and dwb resolves to the dedicated band."""

        node = translate_topology([_root_raw()]).get(_ROOT)

        assert node.led is True
        assert node.dwb is ARWiFiBand.BAND_6G1

    def test_radio_fh_ssid(self) -> None:
        """Fronthaul SSID is captured per radio."""

        radio = (
            translate_topology([_root_raw()])
            .get(_ROOT)
            .radios[ARWiFiBand.BAND_2G1]
        )

        assert radio.ssid == "S2"
        assert radio.ssid_fh == "S2FH"

    def test_wireless_node_config(self) -> None:
        """The wireless node decodes lacp, led and preferred parent."""

        node = translate_topology([_root_raw(), _wl_raw()]).get(_WL)

        assert node.lacp is False
        assert node.led is False
        assert node.preferred_parent == MacAddress(_ROOT)

    def test_backhaul_parent_ssid(self) -> None:
        """Wireless backhaul carries the parent SSID."""

        node = translate_topology([_root_raw(), _wl_raw()]).get(_WL)

        assert node.backhaul.ssid_parent == "PARENT_SSID"

    def test_wired_link_rate(self) -> None:
        """Wired backhaul link rate maps the letter code to ARPortSpeed."""

        node = translate_topology([_root_raw(), _wired_raw()]).get(_WIRED)

        assert node.backhaul.link_rate is ARPortSpeed.MBPS_1000

    def test_consumed_capability_stripped(self) -> None:
        """Decoded keys drop; only the unknown index `9` is kept raw."""

        node = translate_topology([_root_raw()]).get(_ROOT)

        assert node.capability == {"9": "1"}
        assert "27" not in node.capability
        assert "28" not in node.capability

    def test_capability_all_consumed_is_none(self) -> None:
        """Capability with only decoded keys becomes None."""

        raw = _root_raw()
        raw["capability"] = {"27": {"lan_port": {}}, "28": {"wan_port": {}}}

        assert translate_topology([raw]).get(_ROOT).capability is None

    def test_virtual_if(self) -> None:
        """Capability 26 decodes per-band vifs with the free flag."""

        node = translate_topology([_root_raw()]).get(_ROOT)
        vifs = node.virtual_if[ARWiFiBand.BAND_2G1]

        assert [(v.index, v.type, v.free) for v in vifs] == [
            (1, 1, True),
            (4, 8, False),
        ]

    def test_features_decoded(self) -> None:
        """Capability bits become node features."""

        node = translate_topology([_root_raw()]).get(_ROOT)

        assert ARAiMeshFeature.MANUAL_REBOOT in node.features
        assert ARAiMeshFeature.LED_AURA in node.features

    def test_fully_mapped_capability_stripped(self) -> None:
        """Fully-mapped indices drop; unknown index 9 stays."""

        node = translate_topology([_root_raw()]).get(_ROOT)

        assert "1" not in node.capability
        assert "2" not in node.capability
        assert node.capability == {"9": "1"}


class TestVifHelpers:
    """Tests for the vif helpers."""

    @pytest.mark.parametrize(
        ("prefix", "expected"),
        [("wl0.1", (0, 1)), ("wl2.7", (2, 7)), ("bad", (None, None))],
        ids=["unit0", "unit2", "bad"],
    )
    def test_parse_vif_prefix(
        self, prefix: str, expected: tuple[int | None, int | None]
    ) -> None:
        """The vif prefix splits into unit and index."""

        assert _parse_vif_prefix(prefix) == expected

    @pytest.mark.parametrize(
        "capability",
        ["x", {}, {"26": "x"}, {"26": {"wifi_band": "x"}}],
        ids=["not_dict", "empty", "cap_not_dict", "band_not_dict"],
    )
    def test_translate_vifs_empty(self, capability: Any) -> None:
        """Malformed capability 26 yields no vifs."""

        assert _translate_vifs({"capability": capability}) == {}

    def test_translate_vifs_skips_bad_entries(self) -> None:
        """Non-dict bands/vifs and unparseable entries are skipped."""

        raw = {
            "capability": {
                "26": {
                    "wifi_band": {
                        "bad": "x",
                        "band1": {"vif": "x"},
                        "band2": {
                            "vif": {
                                "wl0.1": "x",
                                "bad": {"type": "1"},
                                "wl0.2": {"type": "x"},
                            }
                        },
                    }
                }
            }
        }

        assert _translate_vifs(raw) == {}

    def test_vif_unknown_band(self) -> None:
        """A vif whose unit has no band maps to UNKNOWN."""

        raw = {
            "capability": {
                "26": {"wifi_band": {"b": {"vif": {"wl9.1": {"type": "1"}}}}}
            }
        }

        vifs = _translate_vifs(raw)
        assert list(vifs) == [ARWiFiBand.UNKNOWN]
        assert vifs[ARWiFiBand.UNKNOWN][0] == ARAiMeshVif(1, 1, free=True)


class TestEnrichmentHelpers:
    """Tests for the enrichment helper edge cases."""

    def test_config_flag_missing(self) -> None:
        """Missing section or key yields None."""

        assert _config_flag({}, "ctrl_led", "led_val") is None
        assert _config_flag({"ctrl_led": {}}, "ctrl_led", "led_val") is None

    @pytest.mark.parametrize(
        "config",
        [{}, {"prefer_ap": {}}, {"prefer_ap": {"amas_wlc_target_bssid": 5}}],
        ids=["no_section", "no_key", "not_str"],
    )
    def test_preferred_parent_absent(self, config: dict[str, Any]) -> None:
        """A missing/invalid preferred BSSID yields None."""

        assert _preferred_parent(config) is None

    @pytest.mark.parametrize("dwb", [None, "-1"], ids=["absent", "disabled"])
    def test_dwb_absent(self, dwb: Any) -> None:
        """No dedicated backhaul band yields None."""

        raw = {"dwb_band": dwb} if dwb is not None else {}
        assert _dwb_band(raw, {}) is None

    @pytest.mark.parametrize(
        "raw",
        [{}, {"wired_port": "x"}, {"wired_port": {"wan_port": {"p": {}}}}],
        ids=["no_port", "not_dict", "no_rate"],
    )
    def test_wired_link_rate_unknown(self, raw: dict[str, Any]) -> None:
        """Missing wired link rate is UNKNOWN."""

        assert _wired_link_rate(raw) is ARPortSpeed.UNKNOWN
