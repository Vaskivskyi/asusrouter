"""Tests for the sysinfo module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from asusrouter.modules.common.metrics import ARMetricType
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.sysinfo import (
    ARMemoryType,
    ARSysInfoSource,
    ARSysInfoSourceUniversal,
    ARSysInfoType,
    ARWlanClientCount,
    get_state,
    translate_state,
)
from asusrouter.modules.wifi import ARWiFiBand

M = ARMemoryType
S = ARSysInfoType
C = ARWlanClientCount
B = ARWiFiBand


def _identity(wifi: dict[ARWiFiBand, int] | None = None) -> ARDeviceIdentity:
    """Build a device identity with the given WiFi band map."""

    identity = ARDeviceIdentity()
    if wifi is not None:
        identity._wifi = wifi
    return identity


class TestARSysInfoSource:
    """Tests for the ARSysInfoSource data source."""

    def test_is_data_source(self) -> None:
        """ARSysInfoSource subclasses ARDataSource."""

        assert issubclass(ARSysInfoSource, ARDataSource)

    def test_universal_instance(self) -> None:
        """ARSysInfoSourceUniversal is an ARSysInfoSource instance."""

        assert isinstance(ARSysInfoSourceUniversal, ARSysInfoSource)

    def test_sources_are_equal(self) -> None:
        """All sysinfo sources are equal (router-global)."""

        assert ARSysInfoSource() == ARSysInfoSource()
        assert hash(ARSysInfoSource()) == hash(ARSysInfoSourceUniversal)

    def test_not_equal_to_other_type(self) -> None:
        """Comparison to a non-source returns NotImplemented (False)."""

        assert ARSysInfoSource().__eq__(object()) is NotImplemented
        assert ARSysInfoSource() != object()

    def test_repr(self) -> None:
        """The source has a stable representation."""

        assert repr(ARSysInfoSource()) == "<ARSysInfoSource>"


class TestGetState:
    """Tests for get_state."""

    async def test_returns_response_dict(self) -> None:
        """Returns the callback dict and queries the right endpoint."""

        expected = {"conn_stats_arr": ["1", "2"]}
        callback = AsyncMock(return_value=expected)

        result = await get_state(callback, MagicMock())

        callback.assert_called_once_with(endpoint=AREndpoint.FETCH_SYSINFO)
        assert result == expected

    @pytest.mark.parametrize(
        "response",
        [None, "string", 42, []],
        ids=["none", "str", "int", "list"],
    )
    async def test_non_dict_returns_empty(self, response: Any) -> None:
        """Returns {} when the callback yields a non-dict."""

        callback = AsyncMock(return_value=response)
        result = await get_state(callback, MagicMock())
        assert result == {}

    async def test_accepts_extra_kwargs(self) -> None:
        """Extra kwargs are accepted without error."""

        callback = AsyncMock(return_value={"conn_stats_arr": ["1", "2"]})
        result = await get_state(callback, MagicMock(), extra="ignored")
        assert result == {"conn_stats_arr": ["1", "2"]}


class TestTranslateState:
    """Tests for translate_state."""

    def test_full_pre_388_7(self) -> None:
        """The pre-388.7 format maps every category, JFFS `used / total`."""

        data = {
            "wlc_0_arr": ["11", "11", "11"],
            "wlc_1_arr": ["3", "3", "3"],
            "conn_stats_arr": ["320", "86"],
            "mem_stats_arr": [
                "882.34",
                "240.57",
                "0.00",
                "52.73",
                "0.00",
                "0.00",
                "85328",
                "7.49 / 63.00 MB",
            ],
            "cpu_stats_arr": ["1.98", "2.04", "2.01"],
        }

        assert translate_state(data) == {
            S.WLAN: {
                B.BAND_2G1: {
                    C.ASSOCIATED: 11,
                    C.AUTHORIZED: 11,
                    C.AUTHENTICATED: 11,
                },
                B.BAND_5G1: {
                    C.ASSOCIATED: 3,
                    C.AUTHORIZED: 3,
                    C.AUTHENTICATED: 3,
                },
            },
            S.CONNECTIONS: {ARMetricType.TOTAL: 320, ARMetricType.ACTIVE: 86},
            S.MEMORY: {
                M.TOTAL: 882340000,
                M.FREE: 240570000,
                M.BUFFERS: 0,
                M.CACHE: 52730000,
                M.SWAP_USED: 0,
                M.SWAP_TOTAL: 0,
                M.NVRAM: 85328,
                M.JFFS_FREE: 55510000,
                M.JFFS_USED: 7490000,
                M.JFFS_TOTAL: 63000000,
            },
            S.LOAD_AVERAGE: {1: 1.98, 5: 2.04, 15: 2.01},
        }

    def test_full_from_388_7(self) -> None:
        """From 388.7: single-value JFFS free, plus used and available."""

        data = {
            "conn_stats_arr": ["320", "86"],
            "mem_stats_arr": [
                "882.34",
                "566.32",
                "0.00",
                "20.11",
                "0.00",
                "0.00",
                "73397",
                "61.11",
                "294.60",
                "552.04",
            ],
            "cpu_stats_arr": ["2.21", "1.43", "0.64"],
        }

        assert translate_state(data)[S.MEMORY] == {
            M.TOTAL: 882340000,
            M.FREE: 566320000,
            M.BUFFERS: 0,
            M.CACHE: 20110000,
            M.SWAP_USED: 0,
            M.SWAP_TOTAL: 0,
            M.NVRAM: 73397,
            M.JFFS_FREE: 61110000,
            M.USED: 294600000,
            M.AVAILABLE: 552040000,
        }

    def test_empty_data(self) -> None:
        """No known variables yields an empty result."""

        assert translate_state({}) == {}

    def test_unknown_band_index(self) -> None:
        """A `wlc` index beyond the known bands maps to UNKNOWN."""

        data = {f"wlc_{i}_arr": ["0", "0", "0"] for i in range(4)}
        data["wlc_4_arr"] = ["1", "2", "3"]
        assert translate_state(data)[S.WLAN][B.UNKNOWN] == {
            C.ASSOCIATED: 1,
            C.AUTHORIZED: 2,
            C.AUTHENTICATED: 3,
        }

    def test_wlan_uses_identity_band_order(self) -> None:
        """`wlc` indices map via the device's own band order."""

        wifi = {
            B.BAND_2G1: 3,
            B.BAND_5G1: 0,
            B.BAND_5G2: 1,
            B.BAND_6G1: 2,
        }
        data = {
            "wlc_0_arr": ["1", "1", "1"],
            "wlc_1_arr": ["2", "2", "2"],
            "wlc_2_arr": ["3", "3", "3"],
            "wlc_3_arr": ["4", "4", "4"],
        }

        wlan = translate_state(data, identity=_identity(wifi))[S.WLAN]
        assert wlan[B.BAND_5G1][C.ASSOCIATED] == 1
        assert wlan[B.BAND_5G2][C.ASSOCIATED] == 2
        assert wlan[B.BAND_6G1][C.ASSOCIATED] == 3
        assert wlan[B.BAND_2G1][C.ASSOCIATED] == 4

    def test_wlan_empty_identity_uses_fallback(self) -> None:
        """An identity with no WiFi map falls back to standard ordering."""

        data = {"wlc_0_arr": ["7", "7", "7"]}
        wlan = translate_state(data, identity=_identity())[S.WLAN]
        assert wlan == {
            B.BAND_2G1: {C.ASSOCIATED: 7, C.AUTHORIZED: 7, C.AUTHENTICATED: 7}
        }

    def test_truncated_wlan_and_none_value(self) -> None:
        """Short and non-numeric client arrays skip missing entries."""

        data = {"wlc_0_arr": ["5", "x"]}
        assert translate_state(data)[S.WLAN] == {B.BAND_2G1: {C.ASSOCIATED: 5}}

    def test_truncated_connections(self) -> None:
        """A single connection value yields only the total."""

        data = {"conn_stats_arr": ["10"]}
        assert translate_state(data)[S.CONNECTIONS] == {ARMetricType.TOTAL: 10}

    def test_connection_none_value_skipped(self) -> None:
        """A non-numeric connection value is skipped."""

        data = {"conn_stats_arr": ["x", "5"]}
        assert translate_state(data)[S.CONNECTIONS] == {ARMetricType.ACTIVE: 5}

    def test_memory_invalid_values_skipped(self) -> None:
        """Non-numeric memory and NVRAM values are skipped."""

        data = {
            "mem_stats_arr": [
                "x",
                "10.00",
                "0.00",
                "0.00",
                "0.00",
                "0.00",
                "y",
            ]
        }
        memory = translate_state(data)[S.MEMORY]
        assert M.TOTAL not in memory
        assert M.NVRAM not in memory
        assert memory[M.FREE] == 10000000

    def test_memory_truncated(self) -> None:
        """A short memory array stops at the missing field."""

        data = {"mem_stats_arr": ["882.34", "240.57"]}
        memory = translate_state(data)[S.MEMORY]
        assert memory == {M.TOTAL: 882340000, M.FREE: 240570000}

    def test_jffs_new_format_invalid(self) -> None:
        """A non-numeric single JFFS value yields no JFFS entries."""

        data = {"mem_stats_arr": ["1.00"] * 7 + ["nan_value"]}
        memory = translate_state(data)[S.MEMORY]
        assert M.JFFS_FREE not in memory

    def test_jffs_malformed_used_total(self) -> None:
        """A malformed `used / total` value yields no JFFS entries."""

        data = {"mem_stats_arr": ["1.00"] * 7 + ["x / y MB"]}
        memory = translate_state(data)[S.MEMORY]
        assert M.JFFS_USED not in memory
        assert M.JFFS_TOTAL not in memory
        assert M.JFFS_FREE not in memory

    def test_load_average_truncated_and_none(self) -> None:
        """Short and non-numeric load arrays skip missing entries."""

        data = {"cpu_stats_arr": ["1.5", "bad"]}
        assert translate_state(data)[S.LOAD_AVERAGE] == {1: 1.5}

    def test_accepts_extra_kwargs(self) -> None:
        """Extra kwargs are accepted without error."""

        assert translate_state({}, identity=MagicMock()) == {}
