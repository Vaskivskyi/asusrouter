"""Tests for the traffic interface source."""

from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.error import AsusRouter404Error
from asusrouter.modules.common.metrics import ARMetricType as M
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.traffic.base import ARTrafficSource, ARTrafficType as T
from asusrouter.modules.traffic.interface import (
    ARTrafficInterfaceSource,
    fetch_state,
    source as interface,
    translate_state,
)
from asusrouter.modules.wifi import ARWiFiBand
from asusrouter.tools.identifiers import MacAddress

_ROUTER = "AA:BB:CC:00:00:01"
_OTHER = "AA:BB:CC:00:00:02"


def _identity() -> ARDeviceIdentity:
    """Identity mapping wireless units 0/1/2 to bands."""

    identity = ARDeviceIdentity()
    identity._wifi = {
        ARWiFiBand.BAND_2G1: 0,
        ARWiFiBand.BAND_5G1: 1,
        ARWiFiBand.BAND_6G1: 2,
    }
    return identity


class TestSource:
    """Tests for ARTrafficInterfaceSource."""

    def test_is_traffic_source_no_link(self) -> None:
        """It is a traffic source with no link, target coerced."""

        source = ARTrafficInterfaceSource(_ROUTER)

        assert isinstance(source, ARTrafficSource)
        assert source.link is None
        assert source.target == MacAddress(_ROUTER)

    def test_dedup_by_target(self) -> None:
        """Sources are equal/hash by target only."""

        assert ARTrafficInterfaceSource(_ROUTER) == ARTrafficInterfaceSource(
            _ROUTER
        )
        assert hash(ARTrafficInterfaceSource(_ROUTER)) == hash(
            ARTrafficInterfaceSource(_ROUTER)
        )
        assert ARTrafficInterfaceSource(_ROUTER) != ARTrafficInterfaceSource(
            _OTHER
        )

    def test_stash_swaps(self) -> None:
        """Stash returns the previous sample and stores the new one."""

        source = ARTrafficInterfaceSource()
        now1 = {"WIRED": {"rx": 1, "tx": 2}}
        now2 = {"WIRED": {"rx": 3, "tx": 4}}

        prev, prev_ts = source.stash(now1, "t1")
        assert prev is None
        assert prev_ts is None

        prev, prev_ts = source.stash(now2, "t2")
        assert prev == now1
        assert prev_ts == "t1"


class TestFetch:
    """Tests for _fetch."""

    async def test_modern_used(self) -> None:
        """A non-empty update.cgi result is used without fallback."""

        callback = AsyncMock(return_value={"WIRED": {"rx": 1, "tx": 2}})
        fetch_raw_callback = AsyncMock()

        result = await interface._fetch(callback, fetch_raw_callback)

        assert result == {"WIRED": {"rx": 1, "tx": 2}}
        callback.assert_awaited_once()
        fetch_raw_callback.assert_not_awaited()

    @pytest.mark.parametrize(
        "modern_outcome",
        ["empty", "404"],
        ids=["empty", "not_found"],
    )
    async def test_falls_back_summing_duplicates(
        self, modern_outcome: str
    ) -> None:
        """A missing update.cgi falls back to raw appGet, summing dual-WAN."""

        async def callback(*, endpoint: Any, request: Any) -> Any:
            if modern_outcome == "404":
                raise AsusRouter404Error("nope")
            return {}

        # Raw appGet content with the duplicate INTERNET keys preserved
        fetch_raw_callback = AsyncMock(
            return_value=(
                '{"netdev":{"INTERNET_rx":"0x0a","INTERNET_tx":"0x14",'
                '"INTERNET_rx":"0x01","INTERNET_tx":"0x02"}}'
            )
        )

        result = await interface._fetch(callback, fetch_raw_callback)

        assert result == {"INTERNET": {"rx": 11, "tx": 22}}

    async def test_no_raw_callback(self) -> None:
        """Without a raw callback the fallback yields nothing."""

        callback = AsyncMock(return_value={})

        assert await interface._fetch(callback, None) == {}

    async def test_fallback_non_string(self) -> None:
        """A non-string raw fallback response yields empty counters."""

        callback = AsyncMock(return_value={})
        fetch_raw_callback = AsyncMock(return_value=None)

        assert await interface._fetch(callback, fetch_raw_callback) == {}


class TestGetState:
    """Tests for fetch_state."""

    async def test_first_then_second_sample(self) -> None:
        """First call has no previous; the second carries the first."""

        source = ARTrafficInterfaceSource()
        callback = AsyncMock(return_value={"WIRED": {"rx": 1, "tx": 2}})

        first = await fetch_state(callback, source, identity=None)
        assert first["now"] == {"WIRED": {"rx": 1, "tx": 2}}
        assert first["prev"] is None
        assert first["delta_time"] is None

        second = await fetch_state(callback, source, identity=None)
        assert second["prev"] == {"WIRED": {"rx": 1, "tx": 2}}
        assert isinstance(second["delta_time"], float)
        assert second["delta_time"] >= 0


class TestTranslateState:
    """Tests for translate_state."""

    def test_non_dict(self) -> None:
        """A non-dict input yields an empty result."""

        assert translate_state(None) == {}

    def test_counters_with_zero_speeds_without_history(self) -> None:
        """With no previous sample counters carry zero speeds."""

        data = {"now": {"WIRED": {"rx": 100, "tx": 200}}, "prev": None}

        assert translate_state(data, identity=None) == {
            T.WIRED: {M.RX: 100, M.TX: 200, M.RX_SPEED: 0.0, M.TX_SPEED: 0.0}
        }

    def test_full_map_with_speeds(self) -> None:
        """All interfaces map to links with counters and speeds."""

        data = {
            "now": {
                "WIRED": {"rx": 100, "tx": 200},
                "INTERNET": {"rx": 50, "tx": 60},
                "INTERNET1": {"rx": 8, "tx": 8},
                "BRIDGE": {"rx": 4, "tx": 4},
                "WIRELESS0": {"rx": 10, "tx": 20},
                "LACP1": {"rx": 5, "tx": 7},
                "LACP2": {"rx": 3, "tx": 4},
                "WIRELESS9": {"rx": 1, "tx": 1},
            },
            "prev": {
                "WIRED": {"rx": 20, "tx": 40},
                "INTERNET": {"rx": 10, "tx": 12},
                "INTERNET1": {"rx": 0, "tx": 0},
                "BRIDGE": {"rx": 0, "tx": 0},
                "WIRELESS0": {"rx": 2, "tx": 4},
                "LACP1": {"rx": 1, "tx": 1},
                "LACP2": {"rx": 1, "tx": 1},
            },
            "delta_time": 2.0,
        }

        result = translate_state(data, identity=_identity())

        assert result[T.WIRED] == {
            M.RX: 100,
            M.TX: 200,
            M.RX_SPEED: 320.0,
            M.TX_SPEED: 640.0,
        }
        assert result[T.WAN] == {
            M.RX: 50,
            M.TX: 60,
            M.RX_SPEED: 160.0,
            M.TX_SPEED: 192.0,
        }
        assert result[T.USB] == {
            M.RX: 8,
            M.TX: 8,
            M.RX_SPEED: 32.0,
            M.TX_SPEED: 32.0,
        }
        assert result[ARWiFiBand.BAND_2G1] == {
            M.RX: 10,
            M.TX: 20,
            M.RX_SPEED: 32.0,
            M.TX_SPEED: 64.0,
        }
        assert result[T.LACP1] == {
            M.RX: 5,
            M.TX: 7,
            M.RX_SPEED: 16.0,
            M.TX_SPEED: 24.0,
        }
        # Cumulative LACP = LACP1 + LACP2
        assert result[T.LACP] == {
            M.RX: 8,
            M.TX: 11,
            M.RX_SPEED: 24.0,
            M.TX_SPEED: 36.0,
        }
        # Unknown wireless unit (no band) is skipped
        assert all(link is not ARWiFiBand.UNKNOWN for link in result)

    def test_overflow_zeroes_speed(self) -> None:
        """A negative counter delta (wrap/reset) zeroes only that speed."""

        data = {
            "now": {"WIRED": {"rx": 5, "tx": 200}},
            "prev": {"WIRED": {"rx": 100, "tx": 40}},
            "delta_time": 2.0,
        }

        assert translate_state(data, identity=None)[T.WIRED] == {
            M.RX: 5,
            M.TX: 200,
            # rx wrapped -> 0; tx normal -> computed
            M.RX_SPEED: 0.0,
            M.TX_SPEED: 640.0,
        }

    def test_wireless_skipped_without_identity(self) -> None:
        """Wireless interfaces are skipped when no band map is available."""

        data = {"now": {"WIRELESS0": {"rx": 1, "tx": 2}}, "prev": None}

        assert translate_state(data, identity=None) == {}

    @pytest.mark.parametrize(
        "delta_time",
        [0.0, 0.5, None],
        ids=["zero", "sub_second", "none"],
    )
    def test_short_interval_zeroes_speed(self, delta_time: Any) -> None:
        """Intervals under a second (or absent) yield zero speeds."""

        data = {
            "now": {"WIRED": {"rx": 5, "tx": 6}},
            "prev": {"WIRED": {"rx": 1, "tx": 2}},
            "delta_time": delta_time,
        }

        assert translate_state(data, identity=None)[T.WIRED] == {
            M.RX: 5,
            M.TX: 6,
            M.RX_SPEED: 0.0,
            M.TX_SPEED: 0.0,
        }

    def test_partial_counters(self) -> None:
        """Interfaces with only one counter still map, with a zero speed."""

        data = {"now": {"WIRED": {"rx": 5}}, "prev": None}

        assert translate_state(data, identity=None) == {
            T.WIRED: {M.RX: 5, M.RX_SPEED: 0.0}
        }

    def test_unknown_iface_and_missing_prev_kind(self) -> None:
        """Unknown interfaces drop; a missing prev kind zeroes that speed."""

        data = {
            "now": {
                "FOO": {"rx": 1, "tx": 2},
                "WIRED": {"rx": 100, "tx": 200},
            },
            "prev": {"WIRED": {"rx": 20}},
            "delta_time": 2.0,
        }

        result = translate_state(data, identity=None)

        # FOO is neither static nor wireless -> dropped
        assert list(result) == [T.WIRED]
        # rx has a previous value -> speed; tx has none -> 0
        assert result[T.WIRED] == {
            M.RX: 100,
            M.TX: 200,
            M.RX_SPEED: 320.0,
            M.TX_SPEED: 0.0,
        }


def test_registers_callable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing the submodule registers the interface source."""

    mock_register = Mock()
    monkeypatch.setattr(
        "asusrouter.registry.ARCallableRegistry.register_source",
        mock_register,
    )

    importlib.reload(interface)

    mock_register.assert_called_once_with(
        interface.ARTrafficInterfaceSource,
        fetch_state=interface.fetch_state,
        translate_state=interface.translate_state,
    )
