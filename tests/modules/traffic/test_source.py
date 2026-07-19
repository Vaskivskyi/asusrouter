"""Tests for the traffic source."""

from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.modules.common.metrics import ARMetricType as M
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.traffic import fetch_state, source as traffic_source
from asusrouter.modules.traffic.aimesh import ARTrafficAiMeshSource
from asusrouter.modules.traffic.base import ARTrafficSource, ARTrafficType as T
from asusrouter.modules.traffic.interface import ARTrafficInterfaceSource
from asusrouter.modules.wifi import ARWiFiBand
from asusrouter.tools.identifiers import MacAddress

_ROUTER = "AA:BB:CC:00:00:01"
_REMOTE = "AA:BB:CC:00:00:02"


def _identity() -> ARDeviceIdentity:
    """Identity whose MAC is the connected router."""

    identity = ARDeviceIdentity()
    identity._mac = MacAddress(_ROUTER)
    return identity


def _callback(
    aimesh: dict[Any, Any] | None = None,
    interface: dict[Any, Any] | None = None,
) -> tuple[Any, list[Any]]:
    """Build a fake fetch_data_callback returning per-source-type content."""

    requested: list[Any] = []

    async def callback(sources: Any) -> dict[Any, Any]:
        requested.extend(sources)
        results: dict[Any, Any] = {}
        for source in sources:
            if isinstance(source, ARTrafficInterfaceSource):
                results[source] = interface if interface is not None else {}
            elif isinstance(source, ARTrafficAiMeshSource):
                results[source] = aimesh if aimesh is not None else {}
        return results

    return callback, requested


class TestGetState:
    """Tests for the dispatcher fetch_state."""

    async def test_without_callback(self) -> None:
        """Without a data callback the dispatcher yields nothing."""

        result = await fetch_state(
            AsyncMock(), ARTrafficSource(target=_ROUTER)
        )

        assert result == {}

    async def test_self_merges_both(self) -> None:
        """For the router, AiMesh overlays interface, winning shared keys."""

        callback, requested = _callback(
            aimesh={
                T.WIRED: {M.RX_SPEED: 100.0},
                ARWiFiBand.BAND_2G1: {M.RX_SPEED: 50.0},
            },
            interface={
                T.WIRED: {M.RX: 10, M.RX_SPEED: 999.0},
                T.WAN: {M.RX: 5, M.RX_SPEED: 7.0},
            },
        )

        result = await fetch_state(
            AsyncMock(),
            ARTrafficSource(),
            identity=_identity(),
            fetch_data_callback=callback,
        )

        assert result == {
            # AiMesh speed wins, interface counter kept
            T.WIRED: {M.RX: 10, M.RX_SPEED: 100.0},
            # interface-only link
            T.WAN: {M.RX: 5, M.RX_SPEED: 7.0},
            # AiMesh-only link
            ARWiFiBand.BAND_2G1: {M.RX_SPEED: 50.0},
        }
        types = {type(s) for s in requested}
        assert types == {ARTrafficAiMeshSource, ARTrafficInterfaceSource}

    async def test_self_by_mac(self) -> None:
        """A target equal to the router MAC is treated as self."""

        callback, requested = _callback(interface={T.WAN: {M.RX: 1}})

        result = await fetch_state(
            AsyncMock(),
            ARTrafficSource(T.WAN, _ROUTER),
            identity=_identity(),
            fetch_data_callback=callback,
        )

        assert result == {T.WAN: {M.RX: 1}}
        assert any(isinstance(s, ARTrafficInterfaceSource) for s in requested)

    async def test_remote_aimesh_only(self) -> None:
        """A remote node fetches AiMesh only, never interface."""

        callback, requested = _callback(
            aimesh={ARWiFiBand.BAND_5G1: {M.RX_SPEED: 12.0}},
            interface={T.WAN: {M.RX: 1}},
        )

        result = await fetch_state(
            AsyncMock(),
            ARTrafficSource(target=_REMOTE),
            identity=_identity(),
            fetch_data_callback=callback,
        )

        assert result == {ARWiFiBand.BAND_5G1: {M.RX_SPEED: 12.0}}
        assert not any(
            isinstance(s, ARTrafficInterfaceSource) for s in requested
        )

    async def test_interface_only_link_skips_aimesh(self) -> None:
        """An interface-only link is served without an AiMesh fetch."""

        callback, requested = _callback(
            interface={
                T.WAN: {M.RX: 5},
                T.WIRED: {M.RX: 9},
            }
        )

        result = await fetch_state(
            AsyncMock(),
            ARTrafficSource(T.WAN, _ROUTER),
            identity=_identity(),
            fetch_data_callback=callback,
        )

        # Filtered to the requested link
        assert result == {T.WAN: {M.RX: 5}}
        assert not any(isinstance(s, ARTrafficAiMeshSource) for s in requested)

    async def test_interface_only_link_remote_empty(self) -> None:
        """An interface-only link on a remote node yields nothing."""

        callback, requested = _callback(interface={T.WAN: {M.RX: 5}})

        result = await fetch_state(
            AsyncMock(),
            ARTrafficSource(T.WAN, _REMOTE),
            identity=_identity(),
            fetch_data_callback=callback,
        )

        assert result == {}
        assert requested == []

    async def test_backhaul_aimesh_only(self) -> None:
        """The backhaul link is served by AiMesh, never interface."""

        callback, requested = _callback(
            aimesh={T.BACKHAUL: {M.RX_SPEED: 80.0}},
            interface={T.WAN: {M.RX: 1}},
        )

        result = await fetch_state(
            AsyncMock(),
            ARTrafficSource(T.BACKHAUL, _ROUTER),
            identity=_identity(),
            fetch_data_callback=callback,
        )

        assert result == {T.BACKHAUL: {M.RX_SPEED: 80.0}}
        assert not any(
            isinstance(s, ARTrafficInterfaceSource) for s in requested
        )

    async def test_overlap_link_filters_interface(self) -> None:
        """An overlap link merges, returning only that link."""

        callback, _ = _callback(
            aimesh={T.WIRED: {M.RX_SPEED: 100.0}},
            interface={
                T.WIRED: {M.RX: 10, M.RX_SPEED: 999.0},
                T.WAN: {M.RX: 5},
            },
        )

        result = await fetch_state(
            AsyncMock(),
            ARTrafficSource(T.WIRED, _ROUTER),
            identity=_identity(),
            fetch_data_callback=callback,
        )

        assert result == {T.WIRED: {M.RX: 10, M.RX_SPEED: 100.0}}

    async def test_overlap_link_absent_in_interface(self) -> None:
        """A link missing from the interface result is dropped from it."""

        callback, _ = _callback(
            aimesh={ARWiFiBand.BAND_6G1: {M.RX_SPEED: 5.0}},
            interface={T.WAN: {M.RX: 1}},
        )

        result = await fetch_state(
            AsyncMock(),
            ARTrafficSource(ARWiFiBand.BAND_6G1, _ROUTER),
            identity=_identity(),
            fetch_data_callback=callback,
        )

        assert result == {ARWiFiBand.BAND_6G1: {M.RX_SPEED: 5.0}}

    @pytest.mark.parametrize(
        "value",
        [None, {None: None}],
        ids=["not_dict", "non_dict_content"],
    )
    async def test_bad_fetch_results(self, value: Any) -> None:
        """Non-dict fetch results collapse to an empty state."""

        async def callback(sources: Any) -> Any:
            return value

        result = await fetch_state(
            AsyncMock(),
            ARTrafficSource(target=_REMOTE),
            identity=_identity(),
            fetch_data_callback=callback,
        )

        assert result == {}


def test_registers_dispatcher(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing the module registers the public source."""

    mock_register = Mock()
    monkeypatch.setattr(
        "asusrouter.registry.ARCallableRegistry.register_source",
        mock_register,
    )

    module = importlib.reload(traffic_source)

    mock_register.assert_called_once_with(
        module.ARTrafficSource,
        fetch_state=module.fetch_state,
    )
