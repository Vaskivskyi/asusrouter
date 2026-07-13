"""Tests for asusrouter.modules.ports.status."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.ports import common
from asusrouter.modules.ports.enums import (
    ARPortCablePair,
    ARPortCapability,
    ARPortProperty as P,
    ARPortsInfo,
    ARPortSpeed,
    ARPortType,
)
from asusrouter.modules.ports.status import (
    ARPortCableState,
    native_name,
    read_cable,
    read_devices,
    read_node_info,
    read_port,
    read_role,
    translate_port_status,
)
from asusrouter.modules.usb import ARUSBDeviceType, ARUSBSpeed
from asusrouter.tools.identifiers import MacAddress


@pytest.fixture(autouse=True)
def _reset_warned() -> None:
    """Clear the unknown-port warning cache before each test."""

    common._reported_unknown_ports.clear()


def _caps(*true_caps: ARPortCapability) -> dict[ARPortCapability, bool]:
    """Build a capability dict with the given caps set True."""

    true_set = set(true_caps)
    return {cap: cap in true_set for cap in ARPortCapability if cap.value >= 0}


class TestNativeName:
    """Tests for native_name."""

    @pytest.mark.parametrize(
        ("label", "expected"),
        [
            ("AI", "AI"),
            ("L1", "L1"),
            ("W0", "W0"),
            ("U1", "U1"),
            ("L10", "L10"),
            ("X5", None),
            ("L", None),
            ("LANX", None),
            ("", None),
        ],
        ids=[
            "ai",
            "lan",
            "wan",
            "usb",
            "two_digits",
            "unknown_prefix",
            "no_index",
            "non_digit_index",
            "empty",
        ],
    )
    def test_normalizes(self, label: str, expected: str | None) -> None:
        """Valid labels pass through; unknown ones return None."""

        assert native_name(label) == expected


class TestReadRole:
    """Tests for read_role."""

    @pytest.mark.parametrize(
        ("name", "base_role", "caps", "max_rate", "expected"),
        [
            (
                "AI",
                ARPortType.LAN,
                _caps(ARPortCapability.LAN),
                ARPortSpeed.MBPS_1000,
                ARPortType.AI,
            ),
            (
                "U1",
                ARPortType.USB,
                _caps(ARPortCapability.USB),
                ARUSBSpeed.USB3,
                ARPortType.USB,
            ),
            (
                "L1",
                ARPortType.LAN,
                _caps(ARPortCapability.LAN),
                ARPortSpeed.MBPS_1000,
                ARPortType.LAN,
            ),
            (
                "W0",
                ARPortType.WAN,
                _caps(ARPortCapability.WAN),
                ARPortSpeed.MBPS_1000,
                ARPortType.WAN,
            ),
            (
                "L1",
                ARPortType.LAN,
                _caps(ARPortCapability.LAN, ARPortCapability.SFPP),
                ARPortSpeed.MBPS_10000,
                ARPortType.SFPP,
            ),
            (
                "L1",
                ARPortType.LAN,
                _caps(ARPortCapability.LAN),
                ARPortSpeed.MBPS_10000,
                ARPortType.LAN,
            ),
        ],
        ids=[
            "ai_label_wins",
            "usb",
            "lan",
            "wan",
            "sfpp_override",
            "no_sfpp_cap_stays_lan",
        ],
    )
    def test_resolves_role(
        self,
        name: str,
        base_role: ARPortType,
        caps: dict[ARPortCapability, bool],
        max_rate: Any,
        expected: ARPortType,
    ) -> None:
        """Role resolves from label and capabilities."""

        assert read_role(name, base_role, caps, max_rate) == expected


class TestReadCable:
    """Tests for read_cable."""

    def test_collapses_all_pairs(self) -> None:
        """All four pairs become ARPortCableState entries."""

        values = {
            "brown": "1",
            "brown_len": "2",
            "blue": "3",
            "blue_len": "4",
            "green": "5",
            "green_len": "6",
            "orange": "7",
            "orange_len": "8",
        }

        cable = read_cable(values)

        assert cable[ARPortCablePair.BROWN] == ARPortCableState(1, 2)
        assert cable[ARPortCablePair.ORANGE] == ARPortCableState(7, 8)
        assert len(cable) == 4

    def test_missing_pairs_absent(self) -> None:
        """Only present pairs are included."""

        cable = read_cable({"brown": "1", "brown_len": "2"})

        assert set(cable) == {ARPortCablePair.BROWN}

    def test_no_cable_returns_empty(self) -> None:
        """No cable fields yield an empty mapping."""

        assert read_cable({"is_on": "1"}) == {}


class TestReadDevices:
    """Tests for read_devices."""

    def test_parses_connected_devices(self) -> None:
        """USB devices become ARUSBDevice instances keyed by position."""

        values = {
            "devices": {
                "1": {"type": "modem", "manu": "SAMSUNG", "serial": "RF1"},
                "2": {"type": "storage", "manu": "JetFlash", "serial": "JF1"},
            }
        }

        devices = read_devices(values)

        assert len(devices) == 2
        by_serial = {d.serial: d for d in devices}
        assert by_serial["RF1"].type == ARUSBDeviceType.MODEM
        assert by_serial["RF1"].position == "1"
        assert by_serial["JF1"].type == ARUSBDeviceType.STORAGE

    @pytest.mark.parametrize(
        "values",
        [{}, {"devices": None}, {"devices": {}}],
        ids=["no_field", "none", "empty"],
    )
    def test_no_devices(self, values: dict) -> None:
        """Absent or empty devices yield an empty list."""

        assert read_devices(values) == []


class TestReadNodeInfo:
    """Tests for read_node_info."""

    def test_parses_all_fields(self) -> None:
        """All four members are parsed and typed."""

        info = read_node_info(
            {
                "cd_good_to_go": "1",
                "power_limit": "-1",
                "power_remain": "30",
                "per_port_power_limit": "15",
            }
        )

        assert info[ARPortsInfo.CD_GOOD_TO_GO] is True
        assert info[ARPortsInfo.POWER_LIMIT] == -1
        assert info[ARPortsInfo.POWER_REMAIN] == 30
        assert info[ARPortsInfo.PER_PORT_POWER_LIMIT] == 15

    def test_partial_fields(self) -> None:
        """Only reported members are present."""

        info = read_node_info({"cd_good_to_go": "0"})

        assert info == {ARPortsInfo.CD_GOOD_TO_GO: False}

    def test_empty(self) -> None:
        """Empty input yields an empty mapping."""

        assert read_node_info({}) == {}


class TestReadPort:
    """Tests for read_port."""

    def test_full_lan_port(self) -> None:
        """A LAN port exposes the full extended property set."""

        values = {
            "is_on": "1",
            "cap": "2",
            "max_rate": "1000",
            "link_rate": "1000",
            "seq_no": "0",
            "ui_display": "Port 4",
            "flag": "0",
            "phy_port_id": "3",
            "ext_port_id": "0",
            "ifname": "eth4",
            "brown": "0",
            "brown_len": "0",
            "blue": "0",
            "blue_len": "0",
            "green": "0",
            "green_len": "0",
            "orange": "0",
            "orange_len": "0",
            "linkrecover": "1",
            "timeout": "1",
        }

        port = read_port("L4", values)

        assert port[P.NATIVE_NAME] == "L4"
        assert port[P.STATE] is True
        assert port[P.LINK_RATE] == ARPortSpeed.MBPS_1000
        assert port[P.MAX_RATE] == ARPortSpeed.MBPS_1000
        assert port[P.ROLE] == ARPortType.LAN
        assert port[P.CAPABILITIES] == [ARPortCapability.LAN]
        assert port[P.EXTENDED] is True
        assert port[P.IFNAME] == "eth4"
        assert port[P.UI_DISPLAY] == "Port 4"
        assert port[P.PHY_PORT_ID] == 3
        assert port[P.FLAG] is False
        assert port[P.LINK_RECOVER] is True
        assert P.CABLE in port

    def test_usb_port_subset(self) -> None:
        """A USB port exposes only its reported fields, no cable."""

        values = {
            "is_on": "0",
            "cap": "128",
            "max_rate": "5000",
            "link_rate": "0",
            "seq_no": "0",
            "ui_display": "",
            "flag": "0",
        }

        port = read_port("U1", values)

        assert port[P.ROLE] == ARPortType.USB
        assert port[P.MAX_RATE] == ARUSBSpeed.USB3
        assert port[P.LINK_RATE] == ARUSBSpeed.DOWN
        assert P.CABLE not in port
        assert P.IFNAME not in port
        assert P.PHY_PORT_ID not in port
        assert P.DEVICES not in port

    def test_usb_port_with_devices(self) -> None:
        """A USB port with a connected device exposes DEVICES."""

        values = {
            "is_on": "0",
            "cap": "128",
            "max_rate": "5000",
            "link_rate": "0",
            "devices": {"2": {"type": "storage", "serial": "JF1"}},
        }

        port = read_port("U1", values)

        assert len(port[P.DEVICES]) == 1
        assert port[P.DEVICES][0].serial == "JF1"


class TestTranslatePortStatus:
    """Tests for translate_port_status."""

    def test_translates_full_payload(self) -> None:
        """node_info folds in and ports are keyed by native name."""

        data = {
            "node_info": {
                "12:34:56:78:9A:BC": {"cd_good_to_go": "1"},
            },
            "port_info": {
                "12:34:56:78:9A:BC": {
                    "W0": {
                        "is_on": "1",
                        "cap": "1",
                        "max_rate": "1000",
                        "link_rate": "1000",
                    },
                    "L1": {
                        "is_on": "0",
                        "cap": "2",
                        "max_rate": "1000",
                        "link_rate": "0",
                    },
                },
            },
        }

        result = translate_port_status(data, ARDeviceIdentity())

        node = result[MacAddress("12:34:56:78:9A:BC")]
        assert node.info == {ARPortsInfo.CD_GOOD_TO_GO: True}
        assert {p[P.NATIVE_NAME] for p in node.ports} == {"W0", "L1"}
        w0 = next(p for p in node.ports if p[P.NATIVE_NAME] == "W0")
        assert w0[P.ROLE] == ARPortType.WAN

    def test_keys_are_mac_addresses(self) -> None:
        """The per-node keys are MacAddress instances, not strings."""

        data = {
            "node_info": {},
            "port_info": {"12:34:56:78:9A:BC": {"W0": {"is_on": "1"}}},
        }

        result = translate_port_status(data, ARDeviceIdentity())

        assert all(isinstance(key, MacAddress) for key in result)

    def test_skips_unknown_labels(self) -> None:
        """Unrecognized port labels are dropped."""

        data = {
            "node_info": {},
            "port_info": {"AA:BB:CC:DD:EE:FF": {"ZZ9": {"is_on": "1"}}},
        }

        result = translate_port_status(data, ARDeviceIdentity())

        assert result[MacAddress("AA:BB:CC:DD:EE:FF")].ports == []

    def test_skips_malformed_mac(self) -> None:
        """A MAC that cannot be parsed is dropped."""

        data = {
            "node_info": {},
            "port_info": {"not-a-mac": {"W0": {"is_on": "1"}}},
        }

        assert translate_port_status(data, ARDeviceIdentity()) == {}

    def test_node_info_only_mac(self) -> None:
        """A MAC present only in node_info still appears with no ports."""

        data = {
            "node_info": {"AA:BB:CC:DD:EE:FF": {"power_limit": "5"}},
            "port_info": {},
        }

        result = translate_port_status(data, ARDeviceIdentity())

        node = result[MacAddress("AA:BB:CC:DD:EE:FF")]
        assert node.ports == []
        assert node.info == {ARPortsInfo.POWER_LIMIT: 5}
