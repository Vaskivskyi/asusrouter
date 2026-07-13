"""Tests for the ping module."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest

from asusrouter.const import AR_CALL_RUN_ACTION, RequestType
from asusrouter.modules.common.metrics import ARMetricType as M
from asusrouter.modules.common.status import STATUS_CODE_KEY
from asusrouter.modules.endpoint_v2 import (
    AREndpoint,
    get_endpoint_request_type,
)
from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.ping import (
    ARPingAction,
    ARPingResult,
    ARPingSource,
    ARPingSourceUniversal,
    ARPingStatus,
    get_state,
    run_action,
    translate_state,
)
from asusrouter.modules.ping.source import _RUN_START_DELAY, _build_request
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.identifiers.ip import IpAddress

# A single finished ping run, in response/content order
_ROW = [
    "1.1.1.1",
    "Cloudflare",
    "1",
    "8.44",
    "10.12",
    "12.36",
    "5",
    "5",
    "0.0",
    "1782998188",
]


def _status_callback(value: str | None) -> AsyncMock:
    """Build a get_data_callback returning the given ping status."""

    return AsyncMock(return_value={ARNvramType.DNS_PING_STATUS: value})


class TestARPingStatus:
    """Tests for ARPingStatus."""

    def test_finished(self) -> None:
        """`3` maps to FINISHED."""

        assert ARPingStatus.from_value("3") is ARPingStatus.FINISHED

    def test_unknown(self) -> None:
        """Any other value maps to UNKNOWN."""

        assert ARPingStatus.from_value("1") is ARPingStatus.UNKNOWN


class TestSource:
    """Tests for the ping source."""

    def test_equal_by_type(self) -> None:
        """Sources are equal by exact type."""

        assert ARPingSource() == ARPingSourceUniversal
        assert hash(ARPingSource()) == hash(ARPingSourceUniversal)

    def test_registered(self) -> None:
        """The source resolves to the module get_state callable."""

        assert (
            ARCallReg.get_callable(ARPingSourceUniversal, "get_state")
            is get_state
        )


class TestBuildRequest:
    """Tests for _build_request."""

    def test_contains_db_and_content(self) -> None:
        """The request targets the dns_ping db with all columns."""

        request = _build_request()
        assert "db=dns_ping" in request
        assert "dns_ip" in request
        assert "data_time" in request


class TestGetState:
    """Tests for get_state."""

    @pytest.fixture(autouse=True)
    def mock_sleep(self) -> Iterator[AsyncMock]:
        """Skip the real run-start delay during tests."""

        with patch(
            "asusrouter.modules.ping.source.asyncio.sleep", AsyncMock()
        ) as sleep:
            yield sleep

    async def test_no_data_callback(self) -> None:
        """Without a data callback nothing is fetched."""

        callback = AsyncMock()
        result = await get_state(callback, ARPingSourceUniversal)

        assert result == {}
        callback.assert_not_awaited()

    async def test_default_reads_finished_results(
        self, mock_sleep: AsyncMock
    ) -> None:
        """Without refresh a finished run is read, no run triggered."""

        callback = AsyncMock(return_value={"contents": [_ROW]})
        run_action_callback = AsyncMock(return_value=True)
        get_data_callback = _status_callback("3")

        result = await get_state(
            callback,
            ARPingSourceUniversal,
            get_data_callback=get_data_callback,
            run_action_callback=run_action_callback,
        )

        assert result == [_ROW]
        # No run triggered, but the finished status is still awaited
        run_action_callback.assert_not_awaited()
        mock_sleep.assert_not_awaited()
        get_data_callback.assert_awaited_with(
            ARNvramType.DNS_PING_STATUS, force=True
        )

    async def test_waits_for_in_progress_run(self) -> None:
        """A run in progress (any trigger) is awaited before reading."""

        callback = AsyncMock()
        get_data_callback = _status_callback("1")
        with patch("asusrouter.tools.poll.asyncio.sleep", AsyncMock()):
            result = await get_state(
                callback,
                ARPingSourceUniversal,
                get_data_callback=get_data_callback,
            )

        assert result == {}
        callback.assert_not_awaited()
        get_data_callback.assert_awaited_with(
            ARNvramType.DNS_PING_STATUS, force=True
        )

    async def test_status_non_dict(self) -> None:
        """A non-dict status reply counts as not finished."""

        get_data_callback = AsyncMock(return_value=None)
        with patch("asusrouter.tools.poll.asyncio.sleep", AsyncMock()):
            result = await get_state(
                AsyncMock(),
                ARPingSourceUniversal,
                get_data_callback=get_data_callback,
            )

        assert result == {}

    async def test_empty_contents(self) -> None:
        """Empty rows yield no data."""

        callback = AsyncMock(return_value={"contents": []})
        result = await get_state(
            callback,
            ARPingSourceUniversal,
            get_data_callback=_status_callback("3"),
        )

        assert result == {}

    async def test_non_dict_data(self) -> None:
        """A non-dict diagnostics reply yields no data."""

        callback = AsyncMock(return_value=None)
        result = await get_state(
            callback,
            ARPingSourceUniversal,
            get_data_callback=_status_callback("3"),
        )

        assert result == {}

    async def test_refresh_no_run_action_callback(self) -> None:
        """Refresh without a run-action callback fetches nothing."""

        callback = AsyncMock()
        result = await get_state(
            callback,
            ARPingSourceUniversal,
            get_data_callback=_status_callback("3"),
            refresh=True,
        )

        assert result == {}
        callback.assert_not_awaited()

    async def test_refresh_run_not_started(self) -> None:
        """A run that fails to start drops the results without polling."""

        callback = AsyncMock()
        get_data_callback = _status_callback("3")

        result = await get_state(
            callback,
            ARPingSourceUniversal,
            get_data_callback=get_data_callback,
            run_action_callback=AsyncMock(return_value=False),
            refresh=True,
        )

        assert result == {}
        callback.assert_not_awaited()
        get_data_callback.assert_not_awaited()

    async def test_refresh_runs_then_reads(
        self, mock_sleep: AsyncMock
    ) -> None:
        """A refresh triggers the run, waits, then reads the results."""

        callback = AsyncMock(return_value={"contents": [_ROW]})
        run_action_callback = AsyncMock(return_value=True)

        result = await get_state(
            callback,
            ARPingSourceUniversal,
            get_data_callback=_status_callback("3"),
            run_action_callback=run_action_callback,
            refresh=True,
        )

        assert result == [_ROW]
        run_action_callback.assert_awaited_once_with(ARPingAction())
        mock_sleep.assert_awaited_once_with(_RUN_START_DELAY)
        call = callback.await_args.kwargs
        assert call["endpoint"] == AREndpoint.FETCH_DIAGNOSTICS_DATA


class TestTranslateState:
    """Tests for translate_state."""

    def test_full_row(self) -> None:
        """A complete row translates into a full result."""

        result = translate_state([_ROW])

        ip = IpAddress.from_value_safe("1.1.1.1")
        assert result == {
            ip: ARPingResult(
                alias="Cloudflare",
                valid=True,
                timestamp=1782998188,
                metrics={
                    M.LATENCY_MIN: 8.44,
                    M.LATENCY_AVG: 10.12,
                    M.LATENCY_MAX: 12.36,
                    M.PACKETS_SENT: 5,
                    M.PACKETS_RECEIVED: 5,
                    M.PACKET_LOSS: 0.0,
                },
            )
        }

    def test_short_row(self) -> None:
        """Absent columns fall back to None / empty metrics."""

        result = translate_state([["1.1.1.1"]])

        ip = IpAddress.from_value_safe("1.1.1.1")
        assert result == {ip: ARPingResult()}

    def test_non_list(self) -> None:
        """Non-list input yields an empty mapping."""

        assert translate_state({"contents": []}) == {}

    def test_skips_malformed_rows(self) -> None:
        """Empty rows, non-list rows and bad IPs are skipped."""

        result = translate_state([[], "not-a-row", ["not-an-ip"], _ROW])

        assert list(result) == [IpAddress.from_value_safe("1.1.1.1")]


class TestPingAction:
    """Tests for the ping action."""

    def test_registered(self) -> None:
        """The action resolves to the module run_action callable."""

        assert (
            ARCallReg.get_callable(ARPingAction(), AR_CALL_RUN_ACTION)
            is run_action
        )


class TestRunAction:
    """Tests for run_action."""

    async def test_success(self) -> None:
        """A success status code reports True."""

        callback = AsyncMock(return_value={STATUS_CODE_KEY: "success"})

        result = await run_action(callback, ARPingAction())

        assert result is True
        callback.assert_awaited_once_with(
            endpoint=AREndpoint.RUN_PING, request=None
        )

    async def test_non_success_code(self) -> None:
        """A missing or other status code reports False."""

        callback = AsyncMock(return_value={STATUS_CODE_KEY: "error"})

        assert await run_action(callback, ARPingAction()) is False

    async def test_non_dict_response(self) -> None:
        """A non-dict response reports False."""

        callback = AsyncMock(return_value=None)

        assert await run_action(callback, ARPingAction()) is False


class TestEndpoint:
    """Tests for the ping endpoints."""

    def test_run_ping_is_get(self) -> None:
        """The run endpoint is a GET request."""

        assert (
            get_endpoint_request_type(AREndpoint.RUN_PING) is RequestType.GET
        )
