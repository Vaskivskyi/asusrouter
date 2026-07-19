"""Tests for the clients count source."""

from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.modules.aimesh import ARAiMeshNode, ARAiMeshTopology
from asusrouter.modules.clients import (
    ARClientsCountSource,
    ARClientsCountSourceUniversal,
)
from asusrouter.modules.clients.count import source as count_source
from asusrouter.modules.clients.count.source import fetch_state
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.tools.identifiers import MacAddress

_ROUTER = "AA:BB:CC:00:00:01"
_NODE = "AA:BB:CC:00:00:02"
_C1 = "AA:BB:CC:00:00:11"
_C2 = "AA:BB:CC:00:00:22"
_AIBOARD = "AA:BB:CC:00:00:33"


def _identity(
    *, ai: bool = False, nodes: tuple[str, ...] = ()
) -> ARDeviceIdentity:
    identity = ARDeviceIdentity()
    identity._mac = MacAddress(_ROUTER)
    if ai:
        identity._support[ARSupportType.AI] = True
    if nodes:
        identity.update_aimesh(
            ARAiMeshTopology(
                nodes={
                    MacAddress(mac): ARAiMeshNode(mac=MacAddress(mac))
                    for mac in nodes
                }
            )
        )
    return identity


def _online_wired(mac: str, node: str | None = None) -> dict[str, Any]:
    entry = {"mac": mac, "isOnline": "1", "isWL": "0"}
    if node is not None:
        entry["amesh_papMac"] = node
    return entry


class TestSource:
    """Tests for ARClientsCountSource."""

    def test_is_data_source(self) -> None:
        """Instances subclass ARDataSource."""

        assert issubclass(ARClientsCountSource, ARDataSource)

    def test_equal_by_target(self) -> None:
        """Instances are equal by their target MAC."""

        assert ARClientsCountSource() == ARClientsCountSource()
        assert hash(ARClientsCountSource()) == hash(ARClientsCountSource())
        assert ARClientsCountSource(_NODE) == ARClientsCountSource(_NODE)
        assert ARClientsCountSource(_NODE) != ARClientsCountSource()

    def test_target_setter(self) -> None:
        """The target is parsed to a MAC, settable after init."""

        source = ARClientsCountSource()
        assert source.target is None

        source.target = _NODE
        assert source.target == MacAddress(_NODE)

    def test_repr(self) -> None:
        """Repr identifies the source and its target."""

        assert repr(ARClientsCountSource()) == "<ARClientsCountSource (None,)>"

    def test_universal_instance(self) -> None:
        """The universal instance targets all nodes (no target)."""

        assert isinstance(ARClientsCountSourceUniversal, ARClientsCountSource)
        assert ARClientsCountSourceUniversal.target is None


class TestTargetMacs:
    """Tests for _target_macs resolution."""

    def test_explicit_target(self) -> None:
        """An explicit target is reported alone."""

        macs = count_source._target_macs(
            ARClientsCountSource(_NODE), _identity(nodes=(_ROUTER,))
        )

        assert macs == [MacAddress(_NODE)]

    def test_all_known_nodes(self) -> None:
        """Without a target every known AiMesh node is reported."""

        macs = count_source._target_macs(
            ARClientsCountSource(), _identity(nodes=(_ROUTER, _NODE))
        )

        assert set(macs) == {MacAddress(_ROUTER), MacAddress(_NODE)}

    def test_falls_back_to_router(self) -> None:
        """Without nodes the connected router is reported."""

        macs = count_source._target_macs(ARClientsCountSource(), _identity())

        assert macs == [MacAddress(_ROUTER)]

    def test_no_router_mac(self) -> None:
        """Without nodes or a router MAC there is nothing to report."""

        identity = ARDeviceIdentity()

        assert (
            count_source._target_macs(ARClientsCountSource(), identity) == []
        )


class TestModern:
    """Tests for the modern diagnostics path."""

    async def test_newest_wins(self) -> None:
        """The newest active-client point is returned per node."""

        callback = AsyncMock(return_value={"count": [20, 21, 22]})

        result = await fetch_state(
            callback, ARClientsCountSource(_NODE), identity=_identity()
        )

        assert result == {MacAddress(_NODE): 22}
        assert callback.await_args is not None
        kwargs = callback.await_args.kwargs
        assert kwargs["endpoint"] == (
            AREndpoint.FETCH_DIAGNOSTICS_ACTIVE_CLIENT
        )
        assert "node_mac=AA%3ABB%3ACC%3A00%3A00%3A02" in kwargs["request"]

    async def test_trailing_zero_falls_back_one_point(self) -> None:
        """A single trailing zero uses the previous point."""

        callback = AsyncMock(return_value={"count": [20, 0]})

        result = await fetch_state(
            callback, ARClientsCountSource(_NODE), identity=_identity()
        )

        assert result == {MacAddress(_NODE): 20}

    async def test_two_trailing_zeros_are_zero(self) -> None:
        """Two zeros in a row are a real zero count."""

        callback = AsyncMock(return_value={"count": [20, 0, 0]})

        result = await fetch_state(
            callback, ARClientsCountSource(_NODE), identity=_identity()
        )

        assert result == {MacAddress(_NODE): 0}

    async def test_single_zero_point_is_zero(self) -> None:
        """A lone zero point has no previous point, so it stays zero."""

        callback = AsyncMock(return_value={"count": [0]})

        result = await fetch_state(
            callback, ARClientsCountSource(_NODE), identity=_identity()
        )

        assert result == {MacAddress(_NODE): 0}

    async def test_all_nodes_queried(self) -> None:
        """Every known node is queried and returned."""

        callback = AsyncMock(return_value={"count": [7]})

        result = await fetch_state(
            callback,
            ARClientsCountSource(),
            identity=_identity(nodes=(_ROUTER, _NODE)),
        )

        assert result == {MacAddress(_ROUTER): 7, MacAddress(_NODE): 7}
        assert callback.await_count == 2

    async def test_no_macs_returns_empty(self) -> None:
        """With nothing to report the result is empty and no call is made."""

        callback = AsyncMock()

        result = await fetch_state(
            callback, ARClientsCountSource(), identity=ARDeviceIdentity()
        )

        assert result == {}
        callback.assert_not_awaited()


class TestLegacyFallback:
    """Tests for the legacy counting fallback."""

    async def test_counts_per_node(self) -> None:
        """Empty diagnostics falls back to per-node online counting."""

        async def _dispatch(**kwargs: Any) -> Any:
            if (
                kwargs["endpoint"]
                == AREndpoint.FETCH_DIAGNOSTICS_ACTIVE_CLIENT
            ):
                return {"count": []}
            return {
                "get_clientlist": {
                    _C1: _online_wired(_C1),
                    _C2: _online_wired(_C2, node=_NODE),
                }
            }

        callback = AsyncMock(side_effect=_dispatch)

        result = await fetch_state(
            callback,
            ARClientsCountSource(),
            identity=_identity(nodes=(_ROUTER, _NODE)),
        )

        assert result == {MacAddress(_ROUTER): 1, MacAddress(_NODE): 1}

    async def test_requested_node_without_clients_is_zero(self) -> None:
        """A requested node with no online clients reports zero."""

        async def _dispatch(**kwargs: Any) -> Any:
            if (
                kwargs["endpoint"]
                == AREndpoint.FETCH_DIAGNOSTICS_ACTIVE_CLIENT
            ):
                return {"count": []}
            return {"get_clientlist": {_C1: _online_wired(_C1)}}

        callback = AsyncMock(side_effect=_dispatch)

        result = await fetch_state(
            callback,
            ARClientsCountSource(),
            identity=_identity(nodes=(_ROUTER, _NODE)),
        )

        assert result == {MacAddress(_ROUTER): 1, MacAddress(_NODE): 0}

    async def test_ai_board_excluded(self) -> None:
        """On AI devices the AI board client is excluded from the count."""

        async def _dispatch(**kwargs: Any) -> Any:
            if (
                kwargs["endpoint"]
                == AREndpoint.FETCH_DIAGNOSTICS_ACTIVE_CLIENT
            ):
                return {"count": []}
            return {
                "get_clientlist": {
                    _C1: _online_wired(_C1),
                    _AIBOARD: {**_online_wired(_AIBOARD), "name": "AiBoard-1"},
                }
            }

        callback = AsyncMock(side_effect=_dispatch)

        result = await fetch_state(
            callback, ARClientsCountSource(), identity=_identity(ai=True)
        )

        assert result == {MacAddress(_ROUTER): 1}

    async def test_ai_board_kept_without_ai_support(self) -> None:
        """Without AI support the AI-board-named client is still counted."""

        async def _dispatch(**kwargs: Any) -> Any:
            if (
                kwargs["endpoint"]
                == AREndpoint.FETCH_DIAGNOSTICS_ACTIVE_CLIENT
            ):
                return {"count": []}
            return {
                "get_clientlist": {
                    _C1: _online_wired(_C1),
                    _AIBOARD: {**_online_wired(_AIBOARD), "name": "AiBoard-1"},
                }
            }

        callback = AsyncMock(side_effect=_dispatch)

        result = await fetch_state(
            callback, ARClientsCountSource(), identity=_identity()
        )

        assert result == {MacAddress(_ROUTER): 2}

    async def test_offline_and_nodeless_ignored(self) -> None:
        """Offline clients and clients without a node are not counted."""

        async def _dispatch(**kwargs: Any) -> Any:
            if (
                kwargs["endpoint"]
                == AREndpoint.FETCH_DIAGNOSTICS_ACTIVE_CLIENT
            ):
                return {"count": []}
            return {
                "get_clientlist": {
                    _C1: _online_wired(_C1),
                    _C2: {"mac": _C2, "isOnline": "0", "isWL": "0"},
                }
            }

        callback = AsyncMock(side_effect=_dispatch)

        result = await fetch_state(
            callback, ARClientsCountSource(), identity=_identity()
        )

        assert result == {MacAddress(_ROUTER): 1}


def test_registers_callable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing the module registers the clients count source."""

    mock_register = Mock()
    monkeypatch.setattr(
        "asusrouter.registry.ARCallableRegistry.register_source",
        mock_register,
    )

    module = importlib.reload(count_source)

    mock_register.assert_called_once_with(
        module.ARClientsCountSource,
        fetch_state=module.fetch_state,
    )
