"""Tests for the clients count source."""

from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

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
_C1 = "AA:BB:CC:00:00:11"
_C2 = "AA:BB:CC:00:00:22"
_AIBOARD = "AA:BB:CC:00:00:33"


def _identity(*, ai: bool = False) -> ARDeviceIdentity:
    identity = ARDeviceIdentity()
    identity._mac = MacAddress(_ROUTER)
    if ai:
        identity._support[ARSupportType.AI] = True
    return identity


class TestSource:
    """Tests for ARClientsCountSource."""

    def test_is_data_source_all_equal(self) -> None:
        """Instances subclass ARDataSource and compare equal."""

        assert issubclass(ARClientsCountSource, ARDataSource)
        assert ARClientsCountSource() == ARClientsCountSource()
        assert hash(ARClientsCountSource()) == hash(ARClientsCountSource())

    def test_repr(self) -> None:
        """Repr identifies the source."""

        assert repr(ARClientsCountSource()) == "<ARClientsCountSource>"

    def test_universal_instance(self) -> None:
        """The universal instance is of the source type."""

        assert isinstance(ARClientsCountSourceUniversal, ARClientsCountSource)


class TestGetState:
    """Tests for fetch_state."""

    async def test_modern_newest_wins(self) -> None:
        """The newest active-client point is returned."""

        callback = AsyncMock(return_value={"count": [20, 21, 22]})

        result = await fetch_state(
            callback, ARClientsCountSource(), identity=_identity()
        )

        assert result == 22
        assert callback.await_args is not None
        kwargs = callback.await_args.kwargs
        assert kwargs["endpoint"] == (
            AREndpoint.FETCH_DIAGNOSTICS_ACTIVE_CLIENT
        )
        assert "node_mac=AA%3ABB%3ACC%3A00%3A00%3A01" in kwargs["request"]

    async def test_modern_trailing_zero_is_kept(self) -> None:
        """A trailing zero point is a valid count, not a fallback trigger."""

        callback = AsyncMock(return_value={"count": [20, 0]})

        result = await fetch_state(
            callback, ARClientsCountSource(), identity=_identity()
        )

        assert result == 0

    async def test_modern_empty_falls_back_to_legacy(self) -> None:
        """An empty count list falls back to counting online clients."""

        async def _dispatch(**kwargs: Any) -> Any:
            if (
                kwargs["endpoint"]
                == AREndpoint.FETCH_DIAGNOSTICS_ACTIVE_CLIENT
            ):
                return {"count": []}
            return {
                "get_clientlist": {
                    _C1: {"mac": _C1, "isOnline": "1", "isWL": "0"},
                    _C2: {"mac": _C2, "isOnline": "0", "isWL": "0"},
                }
            }

        callback = AsyncMock(side_effect=_dispatch)

        result = await fetch_state(
            callback, ARClientsCountSource(), identity=_identity()
        )

        assert result == 1

    async def test_modern_unparseable_falls_back(self) -> None:
        """A non-dict modern response falls back to counting."""

        async def _dispatch(**kwargs: Any) -> Any:
            if (
                kwargs["endpoint"]
                == AREndpoint.FETCH_DIAGNOSTICS_ACTIVE_CLIENT
            ):
                return "not-a-dict"
            return {
                "get_clientlist": {
                    _C1: {"mac": _C1, "isOnline": "1", "isWL": "0"}
                }
            }

        callback = AsyncMock(side_effect=_dispatch)

        result = await fetch_state(
            callback, ARClientsCountSource(), identity=_identity()
        )

        assert result == 1

    async def test_legacy_without_identity(self) -> None:
        """Without an identity the online clients are counted."""

        callback = AsyncMock(
            return_value={
                "get_clientlist": {
                    _C1: {"mac": _C1, "isOnline": "1", "isWL": "0"},
                    _C2: {"mac": _C2, "isOnline": "1", "isWL": "0"},
                }
            }
        )

        result = await fetch_state(callback, ARClientsCountSource())

        assert result == 2
        assert callback.await_args is not None
        assert callback.await_args.kwargs["endpoint"] == AREndpoint.FETCH_DATA

    async def test_legacy_ai_board_subtracted(self) -> None:
        """On AI devices the AI board client is excluded from the count."""

        async def _dispatch(**kwargs: Any) -> Any:
            if (
                kwargs["endpoint"]
                == AREndpoint.FETCH_DIAGNOSTICS_ACTIVE_CLIENT
            ):
                return {"count": []}
            return {
                "get_clientlist": {
                    _C1: {"mac": _C1, "isOnline": "1", "isWL": "0"},
                    _AIBOARD: {
                        "mac": _AIBOARD,
                        "name": "AiBoard-1",
                        "isOnline": "1",
                        "isWL": "0",
                    },
                }
            }

        callback = AsyncMock(side_effect=_dispatch)

        result = await fetch_state(
            callback, ARClientsCountSource(), identity=_identity(ai=True)
        )

        assert result == 1

    async def test_legacy_ai_board_kept_without_ai_support(self) -> None:
        """Without AI support the AI-board-named client is still counted."""

        callback = AsyncMock(
            return_value={
                "get_clientlist": {
                    _C1: {"mac": _C1, "isOnline": "1", "isWL": "0"},
                    _AIBOARD: {
                        "mac": _AIBOARD,
                        "name": "AiBoard-1",
                        "isOnline": "1",
                        "isWL": "0",
                    },
                }
            }
        )

        result = await fetch_state(callback, ARClientsCountSource())

        assert result == 2


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
