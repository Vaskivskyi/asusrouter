"""Tests for the speedtest last-result source."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest

from asusrouter.modules.action import _RUN_START_DELAY
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.endpoint.hooks import ARHook
from asusrouter.modules.speedtest import (
    ARSpeedTestAction,
    ARSpeedTestResult,
    ARSpeedTestSource,
    ARSpeedTestSourceUniversal,
    get_state,
    run_action,
    translate_state,
)
from asusrouter.modules.speedtest.source import _log_stream
from asusrouter.registry import ARCallableRegistry as ARCallReg

_HOOK = ARHook.OOKLA_SPEEDTEST_RESULT.value
_EVENTS = [{"type": "result", "result": {"id": "abc"}}, {}]


def _events(result_id: str) -> list[dict]:
    """Build a result stream ending in a result row with the given id."""

    return [{"type": "result", "result": {"id": result_id}}, {}]


def _reply(result_id: str) -> dict:
    """Build a hook reply wrapping a result stream."""

    return {_HOOK: _events(result_id)}


_HISTORY_HOOK = ARHook.OOKLA_SPEEDTEST_HISTORY.value


def _events_srv(result_id: str, server_id: int) -> list[dict]:
    """Build a result stream whose final row is run against a server."""

    return [
        {
            "type": "result",
            "result": {"id": result_id},
            "server": {"id": server_id},
        },
        {},
    ]


class TestSource:
    """Tests for the speedtest source."""

    def test_bare_equal_by_type(self) -> None:
        """A bare source equals the universal auto instance."""

        assert ARSpeedTestSource() == ARSpeedTestSourceUniversal
        assert hash(ARSpeedTestSource()) == hash(ARSpeedTestSourceUniversal)

    def test_bound_is_distinct(self) -> None:
        """A server-bound source differs from the auto source."""

        assert ARSpeedTestSource(54112) != ARSpeedTestSource()
        assert ARSpeedTestSource(54112) != ARSpeedTestSource(11367)

    def test_bound_equal_by_server_and_iface(self) -> None:
        """Bound sources are equal by server id and interface, int or str."""

        assert ARSpeedTestSource(54112) == ARSpeedTestSource("54112")
        assert hash(ARSpeedTestSource(1, "tun11")) == hash(
            ARSpeedTestSource(1, "tun11")
        )

    def test_normalizes_and_validates_server(self) -> None:
        """A positive id is kept as a string; anything else is auto."""

        assert ARSpeedTestSource(54112).server_id == "54112"
        assert ARSpeedTestSource(0).server_id is None
        assert ARSpeedTestSource("nope").server_id is None

    def test_not_equal_other_type(self) -> None:
        """Comparison against a non-source is not equal."""

        assert ARSpeedTestSource() != object()

    def test_registered(self) -> None:
        """Any source instance resolves to the module get_state callable."""

        assert (
            ARCallReg.get_callable(ARSpeedTestSource(54112), "get_state")
            is get_state
        )


class TestGetState:
    """Tests for get_state."""

    @pytest.fixture(autouse=True)
    def mock_sleep(self) -> Iterator[AsyncMock]:
        """Skip the real run-start delay during tests."""

        with patch(
            "asusrouter.modules.action.asyncio.sleep", AsyncMock()
        ) as sleep:
            yield sleep

    async def test_default_reads_result(self) -> None:
        """Without refresh the last result is read, no run triggered."""

        callback = AsyncMock(return_value={_HOOK: _EVENTS})
        result = await get_state(callback, ARSpeedTestSourceUniversal)

        assert result == _EVENTS
        call = callback.await_args.kwargs
        assert call["endpoint"] == AREndpoint.FETCH_DATA

    async def test_extract_non_dict(self) -> None:
        """A non-dict hook reply yields no data."""

        callback = AsyncMock(return_value=None)
        result = await get_state(callback, ARSpeedTestSourceUniversal)

        assert result == {}

    async def test_bound_source_uses_matching_last_run(self) -> None:
        """A bound source keeps the last run when it is for its server."""

        events = _events_srv("r", 54112)
        callback = AsyncMock(return_value={_HOOK: events})

        result = await get_state(callback, ARSpeedTestSource(54112))

        assert result == events

    async def test_bound_source_falls_back_to_history(self) -> None:
        """A last run for another server falls back to stored history."""

        entry = {
            "type": "result",
            "server": {"id": 54112},
            "result": {"id": "h"},
        }
        callback = AsyncMock(
            side_effect=[
                {_HOOK: _events_srv("r", 23314)},  # last run, wrong server
                {_HISTORY_HOOK: [entry]},  # stored run for our server
            ]
        )

        result = await get_state(callback, ARSpeedTestSource(54112))

        assert result == [entry]

    async def test_bound_source_no_data(self) -> None:
        """No matching last run and no history yields no data."""

        callback = AsyncMock(
            side_effect=[
                {_HOOK: _events_srv("r", 23314)},
                {_HISTORY_HOOK: []},
            ]
        )

        result = await get_state(callback, ARSpeedTestSource(54112))

        assert result == {}

    async def test_refresh_missing_run_callback(self) -> None:
        """Refresh without a run-action callback fetches nothing."""

        callback = AsyncMock()
        result = await get_state(
            callback, ARSpeedTestSourceUniversal, refresh=True
        )

        assert result == {}
        callback.assert_not_awaited()

    async def test_refresh_run_not_started(self) -> None:
        """A run that fails to start drops the result without polling."""

        # The prior-id read happens first, then the failed trigger
        callback = AsyncMock(return_value=_reply("old"))
        result = await get_state(
            callback,
            ARSpeedTestSourceUniversal,
            run_action_callback=AsyncMock(return_value=False),
            refresh=True,
        )

        assert result == {}
        callback.assert_awaited_once()

    async def test_refresh_times_out(self) -> None:
        """A run whose result never turns fresh drops the result."""

        # Every read returns the same old result, so it never looks fresh
        callback = AsyncMock(return_value=_reply("old"))
        with patch("asusrouter.tools.poll.asyncio.sleep", AsyncMock()):
            result = await get_state(
                callback,
                ARSpeedTestSourceUniversal,
                run_action_callback=AsyncMock(return_value=True),
                refresh=True,
            )

        assert result == {}

    async def test_refresh_ignores_stale_then_reads_fresh(self) -> None:
        """A lingering old result is skipped until a fresh id appears."""

        fresh = _events("new")
        # prior read (old), first poll still old, then the fresh result
        callback = AsyncMock(
            side_effect=[_reply("old"), _reply("old"), {_HOOK: fresh}]
        )
        run_action_callback = AsyncMock(return_value=True)

        with patch("asusrouter.tools.poll.asyncio.sleep", AsyncMock()):
            result = await get_state(
                callback,
                ARSpeedTestSourceUniversal,
                run_action_callback=run_action_callback,
                refresh=True,
            )

        assert result == fresh
        run_action_callback.assert_awaited_once_with(ARSpeedTestAction())

    async def test_refresh_runs_then_reads(
        self, mock_sleep: AsyncMock
    ) -> None:
        """A refresh triggers the run, waits, then reads the fresh result."""

        fresh = _events("new")
        callback = AsyncMock(side_effect=[_reply("old"), {_HOOK: fresh}])
        run_action_callback = AsyncMock(return_value=True)

        result = await get_state(
            callback,
            ARSpeedTestSourceUniversal,
            run_action_callback=run_action_callback,
            refresh=True,
        )

        assert result == fresh
        run_action_callback.assert_awaited_once_with(ARSpeedTestAction())
        mock_sleep.assert_awaited_once_with(_RUN_START_DELAY)

    async def test_refresh_uses_source_server(self) -> None:
        """The source's bound server/interface drive the run action."""

        fresh = _events("new")
        callback = AsyncMock(side_effect=[_reply("old"), {_HOOK: fresh}])
        run_action_callback = AsyncMock(return_value=True)

        await get_state(
            callback,
            ARSpeedTestSource(54112, "tun11"),
            run_action_callback=run_action_callback,
            refresh=True,
        )

        action = run_action_callback.await_args.args[0]
        assert action.server_id == "54112"
        assert action.iface == "tun11"

    async def test_refresh_aborts_on_error(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An errored run aborts instead of polling to timeout."""

        error_stream = {
            _HOOK: [
                {
                    "type": "log",
                    "message": "No servers defined",
                    "level": "error",
                },
                {},
            ]
        }
        # prior read (old), then the error stream from the failed run
        callback = AsyncMock(side_effect=[_reply("old"), error_stream])

        with (
            patch("asusrouter.tools.poll.asyncio.sleep", AsyncMock()),
            caplog.at_level("DEBUG"),
        ):
            result = await get_state(
                callback,
                ARSpeedTestSourceUniversal,
                run_action_callback=AsyncMock(return_value=True),
                refresh=True,
            )

        assert result == {}
        assert "No servers defined" in caplog.text

    async def test_refresh_save_persists_fresh_result(self) -> None:
        """With save, the fresh raw result row is handed to history."""

        fresh = _events("new")
        callback = AsyncMock(side_effect=[_reply("old"), {_HOOK: fresh}])

        with patch(
            "asusrouter.modules.speedtest.source.async_save_result",
            AsyncMock(return_value=True),
        ) as save:
            result = await get_state(
                callback,
                ARSpeedTestSourceUniversal,
                run_action_callback=AsyncMock(return_value=True),
                refresh=True,
                save=True,
            )

        assert result == fresh
        save.assert_awaited_once_with(callback, fresh[0])

    async def test_refresh_save_failure_still_returns(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A failed save is logged but the result is still returned."""

        fresh = _events("new")
        callback = AsyncMock(side_effect=[_reply("old"), {_HOOK: fresh}])

        with (
            patch(
                "asusrouter.modules.speedtest.source.async_save_result",
                AsyncMock(return_value=False),
            ),
            caplog.at_level("DEBUG"),
        ):
            result = await get_state(
                callback,
                ARSpeedTestSourceUniversal,
                run_action_callback=AsyncMock(return_value=True),
                refresh=True,
                save=True,
            )

        assert result == fresh
        assert "not saved to history" in caplog.text

    async def test_save_ignored_without_refresh(self) -> None:
        """Save has no effect on a plain read."""

        callback = AsyncMock(return_value={_HOOK: _EVENTS})

        with patch(
            "asusrouter.modules.speedtest.source.async_save_result",
            AsyncMock(),
        ) as save:
            result = await get_state(
                callback, ARSpeedTestSourceUniversal, save=True
            )

        assert result == _EVENTS
        save.assert_not_awaited()


class TestLogStream:
    """Tests for the diagnostic _log_stream."""

    def test_not_a_list(self, caplog: pytest.LogCaptureFixture) -> None:
        """A non-list stream is logged as such."""

        with caplog.at_level("DEBUG"):
            _log_stream(None)

        assert "not a list" in caplog.text

    def test_no_typed_row(self, caplog: pytest.LogCaptureFixture) -> None:
        """A stream with no typed row logs a None last type."""

        with caplog.at_level("DEBUG"):
            _log_stream([{}, "x"])

        assert "last type=None" in caplog.text

    def test_typed_rows(self, caplog: pytest.LogCaptureFixture) -> None:
        """The last typed row and item count are logged."""

        with caplog.at_level("DEBUG"):
            _log_stream([{"type": "download"}, {"type": "upload"}, {}])

        assert "3 items" in caplog.text
        assert "last type=upload" in caplog.text

    def test_skips_work_when_debug_off(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Nothing is logged when debug is disabled."""

        with caplog.at_level("INFO", logger="asusrouter.modules.speedtest"):
            _log_stream([{"type": "download"}, {}])

        assert caplog.text == ""


class TestTranslateState:
    """Tests for translate_state."""

    def test_translates_final_result(self) -> None:
        """The final result row becomes a result object."""

        result = translate_state(_EVENTS)

        assert isinstance(result, ARSpeedTestResult)
        assert result.result_id == "abc"

    def test_no_result(self) -> None:
        """A stream without a result yields None."""

        assert translate_state([{"type": "download"}]) is None


class TestRunAction:
    """Tests for run_action."""

    async def test_default(self) -> None:
        """A default run stamps the start time, then posts an empty body."""

        callback = AsyncMock()
        result = await run_action(callback, ARSpeedTestAction())
        assert result.success is True

        # First the start time, then the run trigger
        start, run = callback.await_args_list
        assert start.kwargs["endpoint"] == AREndpoint.SET_SPEEDTEST_START_TIME
        assert start.kwargs["request"].startswith("ookla_start_time=")
        assert run.kwargs["endpoint"] == AREndpoint.RUN_SPEEDTEST
        assert run.kwargs["request"] == "type=&id="

    async def test_with_server_and_iface(self) -> None:
        """A targeted run carries the server id and interface."""

        callback = AsyncMock()
        await run_action(
            callback, ARSpeedTestAction(server_id="42", iface="tun11")
        )

        run = callback.await_args_list[1].kwargs
        assert run["request"] == "type=&id=42&iface=tun11"

    async def test_with_integer_server(self) -> None:
        """An integer server id is sent verbatim."""

        callback = AsyncMock()
        await run_action(callback, ARSpeedTestAction(server_id=54112))

        run = callback.await_args_list[1].kwargs
        assert run["request"] == "type=&id=54112"

    async def test_prefers_raw_callback(self) -> None:
        """With a raw callback, both requests post raw and success is True."""

        callback = AsyncMock()
        raw_callback = AsyncMock(return_value="")

        result = await run_action(
            callback, ARSpeedTestAction(), raw_callback=raw_callback
        )

        assert result.success is True
        callback.assert_not_awaited()
        assert raw_callback.await_count == 2

    async def test_failed_run_returns_false(self) -> None:
        """A failed run request reports False."""

        raw_callback = AsyncMock(return_value=None)

        result = await run_action(
            AsyncMock(), ARSpeedTestAction(), raw_callback=raw_callback
        )

        assert result.success is False

    def test_registered(self) -> None:
        """The action resolves to the module run_action callable."""

        assert (
            ARCallReg.get_callable(ARSpeedTestAction(), "run_action")
            is run_action
        )


class TestAction:
    """Tests for ARSpeedTestAction."""

    def test_normalizes_integer_id(self) -> None:
        """A positive integer server id is stored as its string form."""

        assert ARSpeedTestAction(54112).server_id == "54112"
        assert ARSpeedTestAction("54112").server_id == "54112"

    def test_default_id_is_none(self) -> None:
        """Without an id the auto server is used."""

        assert ARSpeedTestAction().server_id is None

    @pytest.mark.parametrize("value", [0, -5, "0", "abc", ""])
    def test_non_positive_falls_back_to_auto(self, value: int | str) -> None:
        """Zero, negative, or non-numeric ids fall back to the auto server."""

        assert ARSpeedTestAction(value).server_id is None

    def test_equal_by_server_and_iface(self) -> None:
        """Actions are equal by server id and interface, int or str alike."""

        assert ARSpeedTestAction(54112) == ARSpeedTestAction("54112")
        assert hash(ARSpeedTestAction(1, "tun11")) == hash(
            ARSpeedTestAction(1, "tun11")
        )

    def test_not_equal_on_iface(self) -> None:
        """A differing interface makes actions unequal."""

        assert ARSpeedTestAction(1) != ARSpeedTestAction(1, "tun11")

    def test_not_equal_other_type(self) -> None:
        """Comparison against a non-action is not equal."""

        assert ARSpeedTestAction() != object()
