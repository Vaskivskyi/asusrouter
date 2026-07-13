"""Tests for asusrouter.modules.ports.legacy."""

from __future__ import annotations

import pytest

from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.ports import common
from asusrouter.modules.ports.enums import ARPortProperty as P, ARPortSpeed
from asusrouter.modules.ports.legacy import (
    native_name,
    read_ethernet_port_speed,
    translate_ethernet_ports,
)
from asusrouter.tools.identifiers import MacAddress

_MAC = "12:34:56:78:9A:BC"


@pytest.fixture(autouse=True)
def _reset_warned() -> None:
    """Clear the unknown-port warning cache before each test."""

    common._reported_unknown_ports.clear()


def _identity(mac: str | None = _MAC) -> ARDeviceIdentity:
    """Build an identity with the given MAC."""

    identity = ARDeviceIdentity()
    if mac is not None:
        identity._mac = MacAddress(mac)
    return identity


class TestReadEthernetPortSpeed:
    """Tests for read_ethernet_port_speed."""

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            ("t", ARPortSpeed.MBPS_10),
            ("X", ARPortSpeed.DOWN),
            ("M", ARPortSpeed.MBPS_100),
            ("G", ARPortSpeed.MBPS_1000),
            ("Q", ARPortSpeed.MBPS_2500),
            ("F", ARPortSpeed.MBPS_5000),
            ("T", ARPortSpeed.MBPS_10000),
            ("?", ARPortSpeed.UNKNOWN),
            ("", ARPortSpeed.UNKNOWN),
        ],
    )
    def test_reads_code(self, code: str, expected: ARPortSpeed) -> None:
        """A single-letter code maps to its speed; unknown -> UNKNOWN."""

        assert read_ethernet_port_speed(code) == expected


class TestNativeName:
    """Tests for native_name."""

    @pytest.mark.parametrize(
        ("label", "expected"),
        [
            ("WAN 0", "W0"),
            ("LAN 1", "L1"),
            ("LAN 8", "L8"),
            ("USB 1", "U1"),
            ("10G 1", "SFP"),
            ("10G", "SFP"),
            ("XYZ 1", None),
            ("WAN x", None),
        ],
        ids=[
            "wan",
            "lan",
            "lan_8",
            "usb",
            "ten_gig",
            "ten_gig_no_index",
            "unknown_prefix",
            "non_int_index",
        ],
    )
    def test_normalizes(self, label: str, expected: str | None) -> None:
        """Legacy labels normalize to the modern native name."""

        assert native_name(label) == expected


class TestTranslateEthernetPorts:
    """Tests for translate_ethernet_ports."""

    def test_translates_under_identity_mac(self) -> None:
        """Ports are keyed under the device MAC with minimal fields."""

        data = {"portSpeed": {"WAN 0": "G", "LAN 1": "G", "LAN 4": "X"}}

        result = translate_ethernet_ports(data, _identity())

        assert all(isinstance(key, MacAddress) for key in result)
        node = result[MacAddress(_MAC)]
        assert node.info == {}
        ports = {p[P.NATIVE_NAME]: p for p in node.ports}
        assert ports["W0"] == {
            P.NATIVE_NAME: "W0",
            P.STATE: True,
            P.LINK_RATE: ARPortSpeed.MBPS_1000,
            P.EXTENDED: False,
        }
        assert ports["L4"][P.STATE] is False
        assert ports["L4"][P.LINK_RATE] == ARPortSpeed.DOWN

    def test_skips_unknown_labels(self) -> None:
        """Unknown labels are dropped, known ones kept."""

        data = {"portSpeed": {"LAN 1": "G", "XYZ 9": "G"}}

        result = translate_ethernet_ports(data, _identity())

        ports = result[MacAddress(_MAC)].ports
        assert {p[P.NATIVE_NAME] for p in ports} == {"L1"}

    @pytest.mark.parametrize(
        "data",
        [{}, {"portSpeed": {}}, {"portSpeed": None}],
        ids=["empty", "empty_speed", "none_speed"],
    )
    def test_empty_input_returns_empty(self, data: dict) -> None:
        """No port data yields an empty result."""

        assert translate_ethernet_ports(data, _identity()) == {}

    def test_no_mac_returns_empty(self) -> None:
        """Without a device MAC the ports cannot be attributed."""

        data = {"portSpeed": {"LAN 1": "G"}}

        assert translate_ethernet_ports(data, _identity(mac=None)) == {}
