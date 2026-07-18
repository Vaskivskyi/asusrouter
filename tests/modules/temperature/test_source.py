"""Tests for the temperature source."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from asusrouter.config import ARConfig, ARConfigKey as ARConfKey
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.temperature import (
    ARTemperatureSource,
    ARTemperatureSourceUniversal,
    ARTemperatureType,
    fetch_state,
    translate_state,
)
from asusrouter.modules.wifi import ARWiFiBand

T = ARTemperatureType


def _identity(wifi: dict[ARWiFiBand, int] | None = None) -> ARDeviceIdentity:
    """Build a device identity with the given WiFi band map."""

    identity = ARDeviceIdentity()
    if wifi is not None:
        identity._wifi = wifi
    return identity


@pytest.fixture(autouse=True)
def reset_config() -> None:
    """Reset relevant config flags before each test."""

    ARConfig.set(ARConfKey.OPTIMISTIC_TEMPERATURE, False)
    ARConfig.set(ARConfKey.NOTIFIED_OPTIMISTIC_TEMPERATURE, False)


class TestARTemperatureSource:
    """Tests for the ARTemperatureSource data source."""

    def test_is_data_source(self) -> None:
        """ARTemperatureSource subclasses ARDataSource."""

        assert issubclass(ARTemperatureSource, ARDataSource)

    def test_universal_instance(self) -> None:
        """ARTemperatureSourceUniversal is an ARTemperatureSource instance."""

        assert isinstance(ARTemperatureSourceUniversal, ARTemperatureSource)


class TestGetState:
    """Tests for fetch_state."""

    async def test_returns_response_dict(self) -> None:
        """Returns the callback dict and queries the right endpoint."""

        expected = {"curr_cpuTemp": "45"}
        callback = AsyncMock(return_value=expected)

        result = await fetch_state(callback, MagicMock(), identity=_identity())

        callback.assert_called_once_with(endpoint=AREndpoint.FETCH_TEMPERATURE)
        assert result == expected

    @pytest.mark.parametrize(
        "response",
        [None, "string", 42, []],
        ids=["none", "str", "int", "list"],
    )
    async def test_non_dict_returns_empty(self, response: Any) -> None:
        """Returns {} when the callback yields a non-dict."""

        callback = AsyncMock(return_value=response)
        result = await fetch_state(callback, MagicMock(), identity=_identity())
        assert result == {}

    async def test_accepts_extra_kwargs(self) -> None:
        """Extra kwargs are accepted without error."""

        callback = AsyncMock(return_value={"curr_cpuTemp": "50"})
        result = await fetch_state(
            callback,
            MagicMock(),
            identity=_identity(),
            config=MagicMock(),
            extra="ignored",
        )
        assert result == {"curr_cpuTemp": "50"}


class TestTranslateState:
    """Tests for translate_state."""

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (
                {
                    "curr_coreTmp_2_raw": "42",
                    "curr_coreTmp_5_raw": "43",
                    "curr_coreTmp_52_raw": "44",
                    "curr_coreTmp_cpu": "45",
                },
                {
                    T.RADIO_2G1: 42.0,
                    T.RADIO_5G1: 43.0,
                    T.RADIO_5G2: 44.0,
                    T.CPU: 45.0,
                },
            ),
            (
                {
                    "curr_coreTmp_0_raw": "40",
                    "curr_coreTmp_1_raw": "41",
                    "curr_coreTmp_2_raw": "42",
                    "curr_coreTmp_3_raw": "43",
                    "curr_coreTmp_cpu": "50",
                },
                {
                    T.RADIO_2G1: 40.0,
                    T.RADIO_5G1: 41.0,
                    T.RADIO_5G2: 42.0,
                    T.RADIO_6G1: 43.0,
                    T.CPU: 50.0,
                },
            ),
            (
                {
                    "curr_coreTmp_wl0_raw": "38",
                    "curr_coreTmp_wl1_raw": "39",
                    "curr_coreTmp_wl2_raw": "40",
                    "curr_coreTmp_wl3_raw": "41",
                    "curr_cpuTemp": "55",
                },
                {
                    T.RADIO_2G1: 38.0,
                    T.RADIO_5G1: 39.0,
                    T.RADIO_5G2: 40.0,
                    T.RADIO_6G1: 41.0,
                    T.CPU: 55.0,
                },
            ),
            (
                {
                    "curr_coreTmp_wl0_raw": "disabled",
                    "curr_coreTmp_wl1_raw": "43",
                    "curr_cpuTemp": "46",
                },
                {T.RADIO_5G1: 43.0, T.CPU: 46.0},
            ),
            ({"curr_cpuTemp": "55&deg;C"}, {T.CPU: 55.0}),
            (
                {"curr_coreTmp_cpu": "60", "curr_cpuTemp": "55"},
                {T.CPU: 60.0},
            ),
            ({}, {}),
        ],
        ids=[
            "format_2_5_52",
            "format_0_1_2_3",
            "format_wl",
            "disabled_filtered",
            "deg_suffix_stripped",
            "cpu_priority",
            "no_data",
        ],
    )
    def test_translates_raw_variables(
        self, data: dict[str, Any], expected: dict[ARTemperatureType, float]
    ) -> None:
        """Raw JS variables map to typed temperature floats.

        With an empty identity the wlX format uses the static fallback.
        """

        assert translate_state(data, identity=_identity()) == expected

    @pytest.mark.parametrize(
        ("wifi", "data", "expected"),
        [
            (
                {
                    ARWiFiBand.BAND_2G1: 0,
                    ARWiFiBand.BAND_5G1: 1,
                    ARWiFiBand.BAND_6G1: 2,
                },
                {
                    "curr_coreTmp_wl0_raw": "40",
                    "curr_coreTmp_wl1_raw": "41",
                    "curr_coreTmp_wl2_raw": "42",
                },
                {
                    T.RADIO_2G1: 40.0,
                    T.RADIO_5G1: 41.0,
                    T.RADIO_6G1: 42.0,
                },
            ),
            (
                {
                    ARWiFiBand.BAND_2G1: 0,
                    ARWiFiBand.BAND_5G1: 1,
                    ARWiFiBand.BAND_5G2: 2,
                    ARWiFiBand.BAND_6G1: 3,
                },
                {
                    "curr_coreTmp_wl0_raw": "38",
                    "curr_coreTmp_wl1_raw": "39",
                    "curr_coreTmp_wl2_raw": "40",
                    "curr_coreTmp_wl3_raw": "41",
                },
                {
                    T.RADIO_2G1: 38.0,
                    T.RADIO_5G1: 39.0,
                    T.RADIO_5G2: 40.0,
                    T.RADIO_6G1: 41.0,
                },
            ),
        ],
        ids=["tri_band_2_5_6", "quad_band"],
    )
    def test_wl_format_uses_identity_bands(
        self,
        wifi: dict[ARWiFiBand, int],
        data: dict[str, Any],
        expected: dict[ARTemperatureType, float],
    ) -> None:
        """The wlX format maps each index via the device WiFi bands."""

        assert translate_state(data, identity=_identity(wifi)) == expected

    @pytest.mark.parametrize(
        ("optimistic", "data", "expected"),
        [
            (True, {"curr_cpuTemp": "0.04"}, {T.CPU: 40.0}),
            (False, {"curr_cpuTemp": "0.04"}, {T.CPU: 0.04}),
            (True, {"curr_cpuTemp": "45"}, {T.CPU: 45.0}),
        ],
        ids=["scaled", "not_scaled_disabled", "in_range_no_warn"],
    )
    def test_optimistic_scaling(
        self,
        optimistic: bool,
        data: dict[str, Any],
        expected: dict[ARTemperatureType, float],
    ) -> None:
        """Scaling applies only when OPTIMISTIC_TEMPERATURE is enabled."""

        ARConfig.set(ARConfKey.OPTIMISTIC_TEMPERATURE, optimistic)
        assert translate_state(data, identity=_identity()) == expected


@pytest.mark.skip(
    reason="Pending V2 test_data architecture: build an end-to-end test "
    "from rt_ax88u_merlin_388/temperature_001.content"
)
def test_real_device_data_pending_migration() -> None:
    """Placeholder for migrating the real-device temperature fixture.

    The raw response `temperature_001.content` is retained; its old V1
    expected-result module was removed with `AsusData.TEMPERATURE`. Wire
    it through the V2 endpoint read + translate_state once the V2 test
    data format is decided.
    """
