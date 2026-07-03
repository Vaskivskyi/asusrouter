"""Tests for the speedtest data models."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import unquote_plus

from asusrouter.modules.common.metrics import ARMetricType as M
from asusrouter.modules.speedtest.models import (
    EXE_TYPE_LIST,
    EXE_TYPE_RUN,
    ARSpeedTestEventType,
    ARSpeedTestResult,
    ARSpeedTestServer,
    ARSpeedTestState,
    build_history_request,
    build_run_request,
    build_start_time_request,
    history_from_list,
    raw_result_from_events,
    result_from_dict,
    result_from_events,
    result_server_id,
    servers_from_list,
    stream_error_message,
    stream_has_error,
)
from asusrouter.tools.units import DataRateUnitConverter, UnitOfDataRate

# A single finished result row, mirroring the Ookla `result` event shape
_RESULT: dict[str, Any] = {
    "type": "result",
    "timestamp": "2026-01-01T00:00:00Z",
    "ping": {"latency": 1.5, "jitter": 0.2, "low": 1.0, "high": 2.0},
    "download": {"bandwidth": 1000, "bytes": 1, "servers": [{"id": 1}]},
    "upload": {"bandwidth": 500},
    "packetLoss": 0,
    "server": {
        "id": 23314,
        "host": "speedtest.example",
        "port": 8080,
        "name": "Example Inc.",
        "location": "Somewhere",
        "country": "Neverland",
    },
    "result": {"id": "abc-123", "persisted": True},
}


class TestState:
    """Tests for ARSpeedTestState."""

    def test_running(self) -> None:
        """`1` maps to RUNNING."""

        assert ARSpeedTestState.from_value("1") is ARSpeedTestState.RUNNING

    def test_idle(self) -> None:
        """`0` maps to IDLE."""

        assert ARSpeedTestState.from_value("0") is ARSpeedTestState.IDLE

    def test_unknown(self) -> None:
        """An unmapped value maps to UNKNOWN."""

        assert ARSpeedTestState.from_value("9") is ARSpeedTestState.UNKNOWN


class TestEventType:
    """Tests for ARSpeedTestEventType."""

    def test_result(self) -> None:
        """`result` maps to RESULT."""

        assert (
            ARSpeedTestEventType.from_value("result")
            is ARSpeedTestEventType.RESULT
        )

    def test_unknown(self) -> None:
        """An unmapped value maps to UNKNOWN."""

        assert (
            ARSpeedTestEventType.from_value("nope")
            is ARSpeedTestEventType.UNKNOWN
        )


class TestBuildRunRequest:
    """Tests for build_run_request."""

    def test_default_start(self) -> None:
        """A plain start sends only type and id, form-encoded."""

        assert build_run_request(EXE_TYPE_RUN) == "type=&id="

    def test_with_server(self) -> None:
        """A chosen server id is included."""

        assert build_run_request(EXE_TYPE_RUN, server_id="42") == "type=&id=42"

    def test_with_integer_server(self) -> None:
        """Any integer server id is accepted, not just the nearby list."""

        assert build_run_request(EXE_TYPE_RUN, server_id=54112) == (
            "type=&id=54112"
        )

    def test_server_id_zero_not_dropped(self) -> None:
        """A `0` server id survives instead of being treated as unset."""

        assert build_run_request(EXE_TYPE_RUN, server_id=0) == "type=&id=0"

    def test_with_iface(self) -> None:
        """A chosen interface is appended."""

        assert (
            build_run_request(EXE_TYPE_RUN, iface="tun11")
            == "type=&id=&iface=tun11"
        )

    def test_list(self) -> None:
        """A list request carries the list type."""

        assert build_run_request(EXE_TYPE_LIST) == "type=list&id="

    def test_start_time(self) -> None:
        """The start time is form-encoded."""

        assert (
            build_start_time_request(1783106179479)
            == "ookla_start_time=1783106179479"
        )


class TestResultFromDict:
    """Tests for result_from_dict."""

    def test_full(self) -> None:
        """A complete row translates into a full result."""

        result = result_from_dict(_RESULT)

        to_bits = DataRateUnitConverter.convert_to_base
        assert result == ARSpeedTestResult(
            result_id="abc-123",
            timestamp="2026-01-01T00:00:00Z",
            server=ARSpeedTestServer(
                id=23314,
                name="Example Inc.",
                location="Somewhere",
                host="speedtest.example",
                country="Neverland",
                port=8080,
            ),
            metrics={
                M.DOWNLOAD_SPEED: to_bits(
                    1000, UnitOfDataRate.BYTE_PER_SECOND
                ),
                M.UPLOAD_SPEED: to_bits(500, UnitOfDataRate.BYTE_PER_SECOND),
                M.LATENCY: 1.5,
                M.JITTER: 0.2,
                M.LATENCY_MIN: 1.0,
                M.LATENCY_MAX: 2.0,
                M.PACKET_LOSS: 0.0,
            },
        )

    def test_minimal(self) -> None:
        """An empty row yields an empty result."""

        result = result_from_dict({})

        assert result == ARSpeedTestResult()

    def test_non_dict_sections_ignored(self) -> None:
        """Non-dict download/upload/ping/result sections are skipped."""

        result = result_from_dict(
            {
                "download": "x",
                "upload": None,
                "ping": 1,
                "result": "y",
                "server": None,
            }
        )

        assert result.metrics == {}
        assert result.result_id is None
        assert result.server is None

    def test_unparsable_bandwidth(self) -> None:
        """A non-numeric bandwidth is dropped."""

        result = result_from_dict({"download": {"bandwidth": "n/a"}})

        assert M.DOWNLOAD_SPEED not in result.metrics


class TestResultFromEvents:
    """Tests for result_from_events."""

    def test_non_list(self) -> None:
        """A non-list stream yields no result."""

        assert result_from_events("nope") is None

    def test_no_result_row(self) -> None:
        """A stream without a result row yields no result."""

        events = [{"type": "download"}, {"type": "ping"}]

        assert result_from_events(events) is None

    def test_picks_last_result(self) -> None:
        """The last result row wins; noise rows are skipped."""

        first = {**_RESULT, "result": {"id": "first"}}
        last = {**_RESULT, "result": {"id": "last"}}
        events = [first, "noise", {"type": "download"}, last, {}]

        result = result_from_events(events)

        assert result is not None
        assert result.result_id == "last"


class TestRawResultFromEvents:
    """Tests for raw_result_from_events."""

    def test_non_list(self) -> None:
        """A non-list stream yields no raw result."""

        assert raw_result_from_events("nope") is None

    def test_no_result_row(self) -> None:
        """A stream without a result row yields no raw result."""

        assert raw_result_from_events([{"type": "download"}, {}]) is None

    def test_returns_last_raw_row(self) -> None:
        """The last raw result row is returned verbatim."""

        last = {**_RESULT, "result": {"id": "last"}}
        events = [_RESULT, {"type": "upload"}, last, {}]

        assert raw_result_from_events(events) is last


class TestStreamError:
    """Tests for stream error detection."""

    # The real Ookla error row for a bad server id
    _ERROR = {
        "type": "log",
        "timestamp": "2026-07-03T20:20:25Z",
        "message": "Configuration - No servers defined (NoServersException)",
        "level": "error",
    }

    def test_detects_error_level_log(self) -> None:
        """A log row with an error level is a terminal error."""

        assert stream_has_error([self._ERROR, {}]) is True

    def test_message_returned(self) -> None:
        """The error message is extracted."""

        assert (
            stream_error_message([self._ERROR, {}]) == self._ERROR["message"]
        )

    def test_error_field(self) -> None:
        """An explicit error field is detected and its message read."""

        rows = [{"error": "boom"}, {}]
        assert stream_has_error(rows) is True
        assert stream_error_message(rows) == "boom"

    def test_error_type(self) -> None:
        """An error-typed row is a terminal error."""

        assert stream_has_error([{"type": "error"}]) is True

    def test_benign_log_not_error(self) -> None:
        """An informational log is not an error."""

        assert stream_has_error([{"type": "log", "level": "info"}]) is False

    def test_normal_stream_not_error(self) -> None:
        """A normal result stream reports no error."""

        assert stream_has_error([{"type": "result"}, {}]) is False

    def test_non_list(self) -> None:
        """A non-list stream reports no error and no message."""

        assert stream_has_error("nope") is False
        assert stream_error_message("nope") is None

    def test_non_dict_rows_ignored(self) -> None:
        """Non-dict rows in the stream are not errors."""

        assert stream_has_error(["x", {}]) is False

    def test_message_none_when_no_error(self) -> None:
        """No error yields no message."""

        assert stream_error_message([{"type": "result"}]) is None

    def test_error_without_message(self) -> None:
        """An error row without a message yields None for the message."""

        assert stream_error_message([{"type": "error"}]) is None


class TestResultServerId:
    """Tests for result_server_id."""

    def test_reads_and_normalizes(self) -> None:
        """The server id is read and normalized to its string form."""

        assert result_server_id({"server": {"id": 54112}}) == "54112"

    def test_no_server(self) -> None:
        """A row without a server has no server id."""

        assert result_server_id({"result": {"id": "x"}}) is None

    def test_non_dict(self) -> None:
        """A non-dict row has no server id."""

        assert result_server_id("nope") is None


class TestBuildHistoryRequest:
    """Tests for build_history_request."""

    def test_form_encoded_json_lines(self) -> None:
        """Entries become newline-joined JSON in the history field."""

        entries = [{"result": {"id": "a"}}, {"result": {"id": "b"}}]
        request = build_history_request(entries)

        assert request.startswith("speedTest_history=")
        body = unquote_plus(request[len("speedTest_history=") :])
        lines = body.splitlines()
        assert [json.loads(line)["result"]["id"] for line in lines] == [
            "a",
            "b",
        ]


class TestHistoryFromList:
    """Tests for history_from_list."""

    def test_non_list(self) -> None:
        """A non-list history yields an empty list."""

        assert history_from_list(None) == []

    def test_skips_empty_and_non_dict(self) -> None:
        """Empty and non-dict rows are skipped, results kept."""

        results = history_from_list([_RESULT, {}, "x", _RESULT])

        assert len(results) == 2


class TestServersFromList:
    """Tests for servers_from_list."""

    def test_non_list(self) -> None:
        """A non-list response yields an empty list."""

        assert servers_from_list(None) == []

    def test_skips_nameless_and_empty(self) -> None:
        """Rows without a name (including the trailing empty) are skipped."""

        servers = servers_from_list(
            [
                {"id": 1, "name": "A", "location": "L"},
                {"id": 2},
                {},
                "x",
            ]
        )

        assert len(servers) == 1
        assert servers[0].name == "A"
