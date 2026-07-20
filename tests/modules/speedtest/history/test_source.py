"""Tests for the speedtest history source."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock
from urllib.parse import unquote_plus

from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.endpoint.hooks import ARHook
from asusrouter.modules.speedtest.history import (
    MAX_HISTORY,
    ARSpeedTestHistorySource,
    ARSpeedTestHistorySourceUniversal,
    async_latest_for_server,
    async_save_result,
    fetch_state,
    translate_state,
)
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.registry import ARCallableRegistry as ARCallReg


def _identity(*, speedtest: bool = True) -> ARDeviceIdentity:
    """Build an identity with the SpeedTest support flag set."""

    identity = ARDeviceIdentity()
    identity._support[ARSupportType.SPEEDTEST] = speedtest
    return identity


_IDENTITY = _identity()

_HOOK = ARHook.OOKLA_SPEEDTEST_HISTORY.value
_HISTORY = [
    {"type": "result", "result": {"id": "a"}},
    {"type": "result", "result": {"id": "b"}},
    {},
]


def _write_calls(callback: AsyncMock) -> list:
    """Return the history-write calls made on the callback."""

    return [
        call
        for call in callback.await_args_list
        if call.kwargs.get("endpoint") == AREndpoint.WRITE_SPEEDTEST_HISTORY
    ]


class TestSource:
    """Tests for the history source."""

    def test_registered(self) -> None:
        """The source resolves to the module fetch_state callable."""

        assert (
            ARCallReg.get_callable(
                ARSpeedTestHistorySourceUniversal, "fetch_state"
            )
            is fetch_state
        )

    def test_equal_by_type(self) -> None:
        """Sources are equal by exact type."""

        assert ARSpeedTestHistorySource() == ARSpeedTestHistorySourceUniversal


class TestGetState:
    """Tests for fetch_state."""

    async def test_reads_history(self) -> None:
        """The history hook is read and returned raw."""

        callback = AsyncMock(return_value={_HOOK: _HISTORY})
        result = await fetch_state(
            callback, ARSpeedTestHistorySourceUniversal, identity=_IDENTITY
        )

        assert result == _HISTORY
        call = callback.await_args.kwargs
        assert call["endpoint"] == AREndpoint.FETCH_DATA

    async def test_non_dict(self) -> None:
        """A non-dict hook reply yields no data."""

        callback = AsyncMock(return_value=None)
        result = await fetch_state(
            callback, ARSpeedTestHistorySourceUniversal, identity=_IDENTITY
        )

        assert result == {}

    async def test_unsupported_skips_fetch(self) -> None:
        """Without SpeedTest support nothing is fetched."""

        callback = AsyncMock()
        result = await fetch_state(
            callback,
            ARSpeedTestHistorySourceUniversal,
            identity=_identity(speedtest=False),
        )

        assert result == {}
        callback.assert_not_awaited()


class TestTranslateState:
    """Tests for translate_state."""

    def test_translates(self) -> None:
        """Result rows are kept, the trailing empty dropped."""

        results = translate_state(_HISTORY)

        assert [r.result_id for r in results] == ["a", "b"]


class TestLatestForServer:
    """Tests for async_latest_for_server."""

    async def test_returns_newest_match(self) -> None:
        """The first (newest) entry for the server is returned."""

        history = [
            {"type": "result", "server": {"id": 54112}, "result": {"id": "n"}},
            {"type": "result", "server": {"id": 54112}, "result": {"id": "o"}},
            {"type": "result", "server": {"id": 23314}, "result": {"id": "x"}},
        ]
        callback = AsyncMock(return_value={_HOOK: history})

        entry = await async_latest_for_server(callback, "54112")

        assert entry is not None
        assert entry["result"]["id"] == "n"

    async def test_no_match(self) -> None:
        """A server with no stored run yields None."""

        history = [{"type": "result", "server": {"id": 23314}}]
        callback = AsyncMock(return_value={_HOOK: history})

        assert await async_latest_for_server(callback, "54112") is None

    async def test_history_not_a_list(self) -> None:
        """A non-list history yields None."""

        callback = AsyncMock(return_value=None)

        assert await async_latest_for_server(callback, "54112") is None


class TestSaveResult:
    """Tests for async_save_result."""

    async def test_no_id(self) -> None:
        """A result without an id is not saved."""

        callback = AsyncMock()
        assert await async_save_result(callback, {"result": {}}) is False
        callback.assert_not_awaited()

    async def test_none_result(self) -> None:
        """A missing result is not saved."""

        callback = AsyncMock()
        assert await async_save_result(callback, None) is False

    async def test_duplicate_skips_write(self) -> None:
        """A result already in history is not rewritten but counts as saved."""

        callback = AsyncMock(return_value={_HOOK: _HISTORY})
        new = {"type": "result", "result": {"id": "a"}}

        assert await async_save_result(callback, new) is True
        assert _write_calls(callback) == []

    async def test_prepends_new(self) -> None:
        """A fresh result is prepended and written back."""

        callback = AsyncMock(return_value={_HOOK: _HISTORY})
        new = {"type": "result", "result": {"id": "c"}, "packetLoss": 1}

        assert await async_save_result(callback, new) is True

        body = _write_calls(callback)[0].kwargs["request"]
        stored = [
            json.loads(line)
            for line in unquote_plus(body.split("=", 1)[1]).splitlines()
        ]
        # Newest first, old entries kept, trailing empty dropped
        assert [entry["result"]["id"] for entry in stored] == ["c", "a", "b"]

    async def test_caps_history(self) -> None:
        """The stored list is capped to MAX_HISTORY entries."""

        history = [
            {"type": "result", "result": {"id": str(i)}}
            for i in range(MAX_HISTORY + 10)
        ]
        callback = AsyncMock(return_value={_HOOK: history})
        new = {"type": "result", "result": {"id": "new"}}

        await async_save_result(callback, new)

        body = _write_calls(callback)[0].kwargs["request"]
        lines = unquote_plus(body.split("=", 1)[1]).splitlines()
        assert len(lines) == MAX_HISTORY

    async def test_history_not_a_list(self) -> None:
        """A non-list history is treated as empty and the new run written."""

        callback = AsyncMock(return_value=None)
        new = {"type": "result", "result": {"id": "x"}}

        assert await async_save_result(callback, new) is True
        assert len(_write_calls(callback)) == 1
