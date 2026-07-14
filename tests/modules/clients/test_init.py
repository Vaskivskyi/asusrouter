"""Tests for the clients module source."""

from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.modules.clients import (
    ARClient,
    ARClientConnection,
    ARClientsSource,
    get_state,
    source as clients_source,
)
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.source import ARDataSource
from asusrouter.tools.identifiers import MacAddress

_ROUTER = "AA:BB:CC:00:00:01"
_C1 = "AA:BB:CC:00:00:11"


def _identity() -> ARDeviceIdentity:
    identity = ARDeviceIdentity()
    identity._mac = MacAddress(_ROUTER)
    return identity


class TestSource:
    """Tests for ARClientsSource."""

    def test_is_data_source_all_equal(self) -> None:
        """Instances subclass ARDataSource and compare equal."""

        assert issubclass(ARClientsSource, ARDataSource)
        assert ARClientsSource() == ARClientsSource()
        assert hash(ARClientsSource()) == hash(ARClientsSource())

    def test_not_equal_other_type(self) -> None:
        """Comparison to a non-source is not equal."""

        assert ARClientsSource() != "x"

    def test_repr(self) -> None:
        """Repr identifies the source."""

        assert repr(ARClientsSource()) == "<ARClientsSource>"

    def test_merge_history_stashes(self) -> None:
        """First merge returns and stores the current clients."""

        source = ARClientsSource()
        client = ARClient(mac=MacAddress(_C1), online=True)
        current = {MacAddress(_C1): client}

        result = source.merge_history(current)

        assert result == current
        assert source._prev == current

    def test_merge_history_marks_vanished_offline(self) -> None:
        """A previously seen client that vanished is kept, offline."""

        source = ARClientsSource()
        client = ARClient(
            mac=MacAddress(_C1),
            online=True,
            connection=ARClientConnection(),
        )
        source.merge_history({MacAddress(_C1): client})

        result = source.merge_history({})

        kept = result[MacAddress(_C1)]
        assert kept.online is False
        assert kept.connection is None


class TestGetState:
    """Tests for get_state."""

    async def test_fetches_and_builds(self) -> None:
        """The two hooks are fetched and the clients built."""

        callback = AsyncMock(
            return_value={
                "get_clientlist": {
                    _C1: {"mac": _C1, "isOnline": "1", "isWL": "0"}
                }
            }
        )

        result = await get_state(
            callback, ARClientsSource(), identity=_identity()
        )

        assert MacAddress(_C1) in result
        assert callback.await_args is not None
        kwargs = callback.await_args.kwargs
        assert kwargs["endpoint"] == AREndpoint.FETCH_DATA
        assert kwargs["request"] == (
            "hook=get_clientlist();get_clientlist_from_json_database()"
        )

    async def test_without_identity(self) -> None:
        """Builds even without an identity (no router to exclude)."""

        callback = AsyncMock(
            return_value={
                "get_clientlist": {
                    _C1: {"mac": _C1, "isOnline": "1", "isWL": "0"}
                }
            }
        )

        result = await get_state(callback, ARClientsSource())

        assert MacAddress(_C1) in result


def test_registers_callable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing the module registers the clients source."""

    mock_register = Mock()
    monkeypatch.setattr(
        "asusrouter.registry.ARCallableRegistry.register_module",
        mock_register,
    )

    module = importlib.reload(clients_source)

    mock_register.assert_called_once_with(
        module.ARClientsSource,
        get_state=module.get_state,
    )
