"""Tests for the data_transform module."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from asusrouter.modules.data import AsusDataState
from asusrouter.modules.data_transform import (
    MODEL_WITH_6GHZ,
    transform_clients,
    transform_cpu,
    transform_ethernet_ports,
    transform_network,
    transform_wan,
)
from asusrouter.modules.ports import ARPortType
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.modules.wan import ARWANCapability
from asusrouter.modules.wifi import ARWiFiBand

# Support dicts used across tests
_NO_SUPPORT: dict[ARSupportType, Any] = {}
_DUALWAN_SUPPORT: dict[ARSupportType, Any] = {
    ARSupportType.WAN_CAPABILITIES: [ARWANCapability.DUALWAN]
}
_AGGREGATION_SUPPORT: dict[ARSupportType, Any] = {
    ARSupportType.WAN_CAPABILITIES: [ARWANCapability.AGGREGATION]
}
_BOTH_SUPPORT: dict[ARSupportType, Any] = {
    ARSupportType.WAN_CAPABILITIES: [
        ARWANCapability.DUALWAN,
        ARWANCapability.AGGREGATION,
    ]
}


def _description(
    support: dict[ARSupportType, Any] = _NO_SUPPORT,
    wifi: dict[ARWiFiBand, int] | None = None,
    model: str | None = None,
) -> MagicMock:
    """Build a mock ARDeviceIdentity."""

    desc = MagicMock()
    desc.support = support
    desc.wifi = wifi or {}
    desc.model = model
    return desc


class TestTransformNetwork:
    """Tests for transform_network."""

    def test_no_dualwan_returns_data_unchanged(self) -> None:
        """No DUALWAN support → original data returned as-is (no copy)."""

        data = {"wan": {"rx": 100}}
        result = transform_network(data, _description(), None)
        assert result is data

    def test_dualwan_adds_missing_speeds(self) -> None:
        """DUALWAN: interfaces missing rx_speed/tx_speed get 0.0 defaults."""

        data = {"wan": {"rx": 100, "tx": 200}}
        result = transform_network(data, _description(_DUALWAN_SUPPORT), None)
        assert result["wan"]["rx_speed"] == 0.0
        assert result["wan"]["tx_speed"] == 0.0

    def test_dualwan_preserves_existing_speeds(self) -> None:
        """DUALWAN: existing speeds are not overwritten."""

        data = {"wan": {"rx_speed": 5.0, "tx_speed": 3.0}}
        result = transform_network(data, _description(_DUALWAN_SUPPORT), None)
        assert result["wan"]["rx_speed"] == 5.0
        assert result["wan"]["tx_speed"] == 3.0

    def test_dualwan_adds_usb_when_absent_no_history(self) -> None:
        """DUALWAN: missing usb key added as zeroed dict when no history."""

        data = {"wan": {"rx": 0, "tx": 0, "rx_speed": 0.0, "tx_speed": 0.0}}
        result = transform_network(data, _description(_DUALWAN_SUPPORT), None)
        assert result["usb"] == {
            "rx": 0,
            "tx": 0,
            "rx_speed": 0.0,
            "tx_speed": 0.0,
        }

    def test_dualwan_adds_usb_from_history(self) -> None:
        """DUALWAN: missing usb filled from history, speeds reset to 0.0."""

        usb_hist = {"rx": 500, "tx": 300, "rx_speed": 9.9, "tx_speed": 8.8}
        history = MagicMock(spec=AsusDataState)
        history.data = {"usb": usb_hist}
        data: dict[str, Any] = {}
        result = transform_network(
            data, _description(_DUALWAN_SUPPORT), history
        )
        assert result["usb"]["rx"] == 500
        assert result["usb"]["tx"] == 300
        assert result["usb"]["rx_speed"] == 0.0
        assert result["usb"]["tx_speed"] == 0.0

    def test_dualwan_usb_already_present_unchanged(self) -> None:
        """DUALWAN: existing usb key is not modified."""

        data = {"usb": {"rx": 1, "tx": 2, "rx_speed": 1.0, "tx_speed": 2.0}}
        result = transform_network(data, _description(_DUALWAN_SUPPORT), None)
        assert result["usb"]["rx"] == 1

    @pytest.mark.parametrize(
        ("wifi", "model", "expect_6g"),
        [
            # 6g supported, no 5g2 → rename 5ghz2 → 6ghz
            ({ARWiFiBand.BAND_6G1: 2}, None, True),
            # Model in MODEL_WITH_6GHZ → rename regardless of wifi flags
            ({}, MODEL_WITH_6GHZ[0], True),
            # 5g2 present → keep as 5ghz2
            ({ARWiFiBand.BAND_5G2: 1, ARWiFiBand.BAND_6G1: 2}, None, False),
            # Neither condition → keep as 5ghz2
            ({}, None, False),
        ],
    )
    def test_dualwan_5ghz2_rename(
        self,
        wifi: dict[ARWiFiBand, int],
        model: str | None,
        expect_6g: bool,
    ) -> None:
        """DUALWAN: 5ghz2 renamed to 6ghz under correct conditions."""

        data = {"5ghz2": {"rx": 0}}
        result = transform_network(
            data, _description(_DUALWAN_SUPPORT, wifi, model), None
        )
        if expect_6g:
            assert "6ghz" in result
            assert "5ghz2" not in result
        else:
            assert "5ghz2" in result
            assert "6ghz" not in result

    def test_dualwan_returns_copy_not_original(self) -> None:
        """DUALWAN: transform_network returns a copy, not the input dict."""

        data: dict[str, Any] = {}
        result = transform_network(data, _description(_DUALWAN_SUPPORT), None)
        assert result is not data


class TestTransformClients:
    """Tests for transform_clients."""

    def test_valid_mac_is_processed(self) -> None:
        """Valid MAC addresses pass through process_client."""

        mac = "AA:BB:CC:11:22:33"
        client_data: dict[str, Any] = {"name": "device"}

        with patch(
            "asusrouter.modules.data_transform.process_client",
            return_value={"processed": True},
        ) as mock_pc:
            result = transform_clients({mac: client_data}, None)

        assert mac in result
        assert result[mac] == {"processed": True}
        mock_pc.assert_called_once_with(client_data, None)

    def test_invalid_mac_is_skipped(self) -> None:
        """Non-MAC keys are excluded from the result."""

        result = transform_clients({"not-a-mac": {}, "also_bad": {}}, None)
        assert result == {}

    def test_empty_data_returns_empty(self) -> None:
        """Empty input → empty output."""

        assert transform_clients({}, None) == {}

    def test_history_passed_to_process_client(self) -> None:
        """Client history is looked up from history state and passed along."""

        mac = "AA:BB:CC:11:22:33"
        history_state = MagicMock(spec=AsusDataState)
        history_state.data = {mac: {"prev_name": "old"}}

        with patch(
            "asusrouter.modules.data_transform.process_client",
            return_value={},
        ) as mock_pc:
            transform_clients({mac: {}}, history_state)

        mock_pc.assert_called_once_with({}, {"prev_name": "old"})

    def test_no_history_passes_none_to_process_client(self) -> None:
        """None history → None client_history passed to process_client."""

        mac = "AA:BB:CC:11:22:33"
        with patch(
            "asusrouter.modules.data_transform.process_client",
            return_value={},
        ) as mock_pc:
            transform_clients({mac: {}}, None)

        mock_pc.assert_called_once_with({}, None)


class TestTransformCpu:
    """Tests for transform_cpu."""

    def test_adds_usage_none_when_missing(self) -> None:
        """Adds usage: None for cores missing the key."""

        data: dict[str, Any] = {"core_1": {"load": 50}}
        result = transform_cpu(data)
        assert result["core_1"]["usage"] is None

    def test_preserves_existing_usage(self) -> None:
        """Existing usage value is not overwritten."""

        data: dict[str, Any] = {"core_1": {"usage": 75}}
        result = transform_cpu(data)
        assert result["core_1"]["usage"] == 75

    def test_mutates_and_returns_input(self) -> None:
        """Returns the same dict object (in-place mutation)."""

        data: dict[str, Any] = {"core_1": {}}
        result = transform_cpu(data)
        assert result is data

    def test_empty_data(self) -> None:
        """Empty dict → empty dict returned."""

        assert transform_cpu({}) == {}


class TestTransformEthernetPorts:
    """Tests for transform_ethernet_ports."""

    def test_non_porttype_key_returns_as_is(self) -> None:
        """Any non-ARPortType key → return original data unchanged."""

        data: dict[Any, Any] = {"string_key": {}}
        result = transform_ethernet_ports(data, "AA:BB:CC:11:22:33")
        assert result is data

    def test_porttype_keys_no_mac_returns_as_is(self) -> None:
        """All ARPortType keys but no mac → return original data unchanged."""

        data: dict[Any, Any] = {ARPortType.LAN: {}}
        result = transform_ethernet_ports(data, None)
        assert result is data

    def test_porttype_keys_with_mac_wraps_in_mac_dict(self) -> None:
        """All ARPortType keys + mac → wraps in {mac: data}."""

        data: dict[Any, Any] = {ARPortType.LAN: {"port_1": True}}
        mac = "AA:BB:CC:11:22:33"
        result = transform_ethernet_ports(data, mac)
        assert result == {mac: data}

    def test_empty_data_with_mac_returns_wrapped(self) -> None:
        """Empty dict with ARPortType keys passes ARPortType check, wraps."""

        data: dict[Any, Any] = {}
        mac = "AA:BB:CC:11:22:33"
        result = transform_ethernet_ports(data, mac)
        assert result == {mac: data}

    def test_mixed_keys_first_non_porttype_exits_early(self) -> None:
        """Mixed keys: first non-ARPortType triggers early return."""

        data: dict[Any, Any] = {"bad_key": {}, ARPortType.LAN: {}}
        result = transform_ethernet_ports(data, "AA:BB:CC:11:22:33")
        assert result is data


class TestTransformWan:
    """Tests for transform_wan."""

    def test_none_support_returns_copy(self) -> None:
        """None support → copy of data with all keys preserved."""

        data = {"dualwan": True, "aggregation": False, "extra": 1}
        result = transform_wan(data, None)
        assert result == data
        assert result is not data

    def test_empty_support_returns_copy(self) -> None:
        """Empty support dict → copy of data with all keys preserved."""

        data = {"dualwan": True}
        result = transform_wan(data, {})
        assert result == data

    def test_no_dualwan_support_pops_dualwan(self) -> None:
        """DUALWAN not in capabilities → dualwan key removed."""

        # _AGGREGATION_SUPPORT is truthy and lacks DUALWAN
        data = {"dualwan": True, "aggregation": False}
        result = transform_wan(data, _AGGREGATION_SUPPORT)
        assert "dualwan" not in result
        assert "aggregation" in result

    def test_no_aggregation_support_pops_aggregation(self) -> None:
        """AGGREGATION not in capabilities → aggregation key removed."""

        data = {"dualwan": True, "aggregation": False}
        result = transform_wan(data, _DUALWAN_SUPPORT)
        assert "dualwan" in result
        assert "aggregation" not in result

    def test_dualwan_only_keeps_dualwan(self) -> None:
        """DUALWAN available → dualwan preserved; aggregation removed."""

        data = {"dualwan": True, "aggregation": False}
        result = transform_wan(data, _DUALWAN_SUPPORT)
        assert "dualwan" in result

    def test_both_capabilities_keeps_both(self) -> None:
        """Both DUALWAN and AGGREGATION available → both keys kept."""

        data = {"dualwan": True, "aggregation": True}
        result = transform_wan(data, _BOTH_SUPPORT)
        assert "dualwan" in result
        assert "aggregation" in result

    def test_missing_keys_not_error(self) -> None:
        """Keys already absent → pop is safe, no KeyError."""

        data: dict[str, Any] = {}
        result = transform_wan(data, _NO_SUPPORT)
        assert result == {}

    def test_returns_copy_not_original(self) -> None:
        """Always returns a copy, never mutates input."""

        data = {"dualwan": True}
        result = transform_wan(data, _BOTH_SUPPORT)
        assert result is not data
