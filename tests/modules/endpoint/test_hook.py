"""Tests for the Hook endpoint module."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from asusrouter.modules.endpoint.hook import process_gwlan, process_wlan
from asusrouter.modules.wifi import ARWiFiBand

# Minimal MAP entries used in patched tests: one plain key, one with a method.
_MAP_PLAIN = [("wl{}_ssid",)]
_MAP_WITH_METHOD = [("wl{}_enabled", lambda v: v is not None)]


class TestProcessGwlan:
    """Tests for process_gwlan."""

    def test_empty_wlan_list_returns_empty(self) -> None:
        """Empty wlan_list → empty dict."""

        assert process_gwlan({}, {}) == {}

    @pytest.mark.parametrize(
        "gid",
        [1, 2, 3],
    )
    def test_produces_keys_for_each_gid(self, gid: int) -> None:
        """Each gid (1-3) produces a key per band."""

        with patch("asusrouter.modules.endpoint.hook.MAP_GWLAN", _MAP_PLAIN):
            result = process_gwlan({}, {ARWiFiBand.BAND_2G1: 0})

        assert f"2g1_{gid}" in result

    def test_band_value_used_as_key_prefix(self) -> None:
        """band.value (e.g. '5g1') is the prefix in the result key."""

        with patch("asusrouter.modules.endpoint.hook.MAP_GWLAN", _MAP_PLAIN):
            result = process_gwlan({}, {ARWiFiBand.BAND_5G1: 1})

        assert any(k.startswith("5g1_") for k in result)

    def test_reads_data_by_formatted_key(self) -> None:
        """Values are read from data using the formatted NVRAM key."""

        data = {"wl0.1_ssid": "MyNet", "wl0.2_ssid": "MyNet2"}
        with patch("asusrouter.modules.endpoint.hook.MAP_GWLAN", _MAP_PLAIN):
            result = process_gwlan(data, {ARWiFiBand.BAND_2G1: 0})

        assert result["2g1_1"]["ssid"] == "MyNet"
        assert result["2g1_2"]["ssid"] == "MyNet2"

    def test_method_applied_to_value(self) -> None:
        """Method in MAP entry is applied to the raw value."""

        data = {"wl0.1_enabled": "yes"}
        with patch(
            "asusrouter.modules.endpoint.hook.MAP_GWLAN", _MAP_WITH_METHOD
        ):
            result = process_gwlan(data, {ARWiFiBand.BAND_2G1: 0})

        # lambda: v is not None → True for "yes"
        assert result["2g1_1"]["enabled"] is True

    def test_multiple_bands(self) -> None:
        """Multiple bands produce disjoint key sets."""

        with patch("asusrouter.modules.endpoint.hook.MAP_GWLAN", _MAP_PLAIN):
            result = process_gwlan(
                {},
                {ARWiFiBand.BAND_2G1: 0, ARWiFiBand.BAND_5G1: 1},
            )

        assert any(k.startswith("2g1_") for k in result)
        assert any(k.startswith("5g1_") for k in result)


class TestProcessWlan:
    """Tests for process_wlan."""

    def test_empty_wlan_list_returns_empty(self) -> None:
        """Empty wlan_list → empty dict."""

        assert process_wlan({}, {}) == {}

    def test_band_value_used_as_key(self) -> None:
        """band.value (e.g. '2g1') is the direct result key."""

        with patch("asusrouter.modules.endpoint.hook.MAP_WLAN", _MAP_PLAIN):
            result = process_wlan({}, {ARWiFiBand.BAND_2G1: 0})

        assert "2g1" in result

    def test_reads_data_by_formatted_key(self) -> None:
        """Values read from data using the index-formatted NVRAM key."""

        data = {"wl0_ssid": "HomeNet", "wl1_ssid": "HomeNet5G"}
        with patch("asusrouter.modules.endpoint.hook.MAP_WLAN", _MAP_PLAIN):
            result = process_wlan(
                data,
                {ARWiFiBand.BAND_2G1: 0, ARWiFiBand.BAND_5G1: 1},
            )

        assert result["2g1"]["ssid"] == "HomeNet"
        assert result["5g1"]["ssid"] == "HomeNet5G"

    def test_method_applied_to_value(self) -> None:
        """Method in MAP entry is applied to the raw value."""

        data = {"wl0_enabled": "yes"}
        with patch(
            "asusrouter.modules.endpoint.hook.MAP_WLAN", _MAP_WITH_METHOD
        ):
            result = process_wlan(data, {ARWiFiBand.BAND_2G1: 0})

        assert result["2g1"]["enabled"] is True

    def test_missing_key_in_data_returns_none(self) -> None:
        """Missing NVRAM key → None value in result."""

        with patch("asusrouter.modules.endpoint.hook.MAP_WLAN", _MAP_PLAIN):
            result = process_wlan({}, {ARWiFiBand.BAND_2G1: 0})

        assert result["2g1"]["ssid"] is None

    def test_multiple_bands(self) -> None:
        """Multiple bands produce separate entries."""

        with patch("asusrouter.modules.endpoint.hook.MAP_WLAN", _MAP_PLAIN):
            result = process_wlan(
                {},
                {ARWiFiBand.BAND_2G1: 0, ARWiFiBand.BAND_5G1: 1},
            )

        assert "2g1" in result
        assert "5g1" in result
