"""SpeedTest data models for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import json
from typing import Any

from asusrouter.const import UNKNOWN_MEMBER_STR, RequestType
from asusrouter.modules.common.metrics import ARMetricType
from asusrouter.tools.converters_v2.raw import (
    raw_to_float,
    raw_to_int,
    raw_to_str,
)
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.units import DataRateUnitConverter, UnitOfDataRate
from asusrouter.tools.writers import dict_to_request


class ARSpeedTestState(FromStrMixin, StrEnum):
    """SpeedTest run state reported in nvram `ookla_state`."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    IDLE = "0"
    RUNNING = "1"
    ERROR_DISCONNECTED = "2"
    ERROR_TIMEOUT = "3"
    ERROR_TERMINATED = "4"
    ERROR_UNKNOWN = "5"


class ARSpeedTestEventType(FromStrMixin, StrEnum):
    """Event type of a row in the Ookla result stream."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    DOWNLOAD = "download"
    ERROR = "error"
    LOG = "log"
    RESULT = "result"
    TEST_START = "testStart"
    UPLOAD = "upload"


# Ookla marks a failed run (bad server, disconnect) with this log level
_ERROR_LEVEL = "error"


@dataclass
class ARSpeedTestServer:
    """A speedtest server."""

    id: int | None = None
    name: str | None = None
    location: str | None = None
    host: str | None = None
    country: str | None = None
    port: int | None = None


@dataclass
class ARSpeedTestResult:
    """A completed speedtest result."""

    result_id: str | None = None
    timestamp: str | None = None
    server: ARSpeedTestServer | None = None
    metrics: dict[ARMetricType, float | int] = field(default_factory=dict)


# The exe.cgi trigger accepts `type` (empty to run, `list` to fetch servers),
# an optional server `id`, and the `iface` to test over
EXE_TYPE_RUN = ""
EXE_TYPE_LIST = "list"


def normalize_server_id(value: int | str | None) -> str | None:
    """Coerce a server id to its wire string, or None for the auto server."""

    parsed = raw_to_int(value)
    return str(parsed) if parsed is not None and parsed > 0 else None


def build_run_request(
    exe_type: str,
    server_id: int | str | None = None,
    iface: str | None = None,
) -> str:
    """Build the `ookla_speedtest_exe.cgi` request body."""

    # Pass id through so a `0` is not dropped; None becomes an empty field
    data: dict[str, Any] = {"type": exe_type, "id": server_id}
    if iface:
        data["iface"] = iface
    return dict_to_request(data, request_type=RequestType.GET)


def build_start_time_request(timestamp_ms: int) -> str:
    """Build the `set_ookla_speedtest_start_time.cgi` request body."""

    return dict_to_request(
        {"ookla_start_time": timestamp_ms}, request_type=RequestType.GET
    )


def build_history_request(entries: list[dict[str, Any]]) -> str:
    """Build the `ookla_speedtest_write_history.cgi` request body."""

    body = "".join(
        json.dumps(entry, separators=(",", ":")) + "\n" for entry in entries
    )
    return dict_to_request(
        {"speedTest_history": body}, request_type=RequestType.GET
    )


# Bandwidth arrives in bytes/s; store rate in bits/s as base units
def _bandwidth_to_bits(value: Any) -> float | None:
    """Convert a bytes/s bandwidth into bits/s, or None if unparsable."""

    raw = raw_to_float(value)
    if raw is None:
        return None
    return DataRateUnitConverter.convert_to_base(
        raw, UnitOfDataRate.BYTE_PER_SECOND
    )


def _server_from_dict(data: Any) -> ARSpeedTestServer | None:
    """Build a server from a result `server` object."""

    if not isinstance(data, dict):
        return None
    return ARSpeedTestServer(
        id=raw_to_int(data.get("id")),
        name=raw_to_str(data.get("name")),
        location=raw_to_str(data.get("location")),
        host=raw_to_str(data.get("host")),
        country=raw_to_str(data.get("country")),
        port=raw_to_int(data.get("port")),
    )


def result_from_dict(data: dict[str, Any]) -> ARSpeedTestResult:
    """Build a result from a single Ookla `result` object."""

    metrics: dict[ARMetricType, float | int] = {}

    download = data.get("download")
    if isinstance(download, dict):
        value = _bandwidth_to_bits(download.get("bandwidth"))
        if value is not None:
            metrics[ARMetricType.DOWNLOAD_SPEED] = value

    upload = data.get("upload")
    if isinstance(upload, dict):
        value = _bandwidth_to_bits(upload.get("bandwidth"))
        if value is not None:
            metrics[ARMetricType.UPLOAD_SPEED] = value

    ping = data.get("ping")
    if isinstance(ping, dict):
        # `low`/`high` bound the latency samples over the run
        for key, metric in (
            ("latency", ARMetricType.LATENCY),
            ("jitter", ARMetricType.JITTER),
            ("low", ARMetricType.LATENCY_MIN),
            ("high", ARMetricType.LATENCY_MAX),
        ):
            value = raw_to_float(ping.get(key))
            if value is not None:
                metrics[metric] = value

    packet_loss = raw_to_float(data.get("packetLoss"))
    if packet_loss is not None:
        metrics[ARMetricType.PACKET_LOSS] = packet_loss

    result = data.get("result")
    result_id = (
        raw_to_str(result.get("id")) if isinstance(result, dict) else None
    )

    return ARSpeedTestResult(
        result_id=result_id,
        timestamp=raw_to_str(data.get("timestamp")),
        server=_server_from_dict(data.get("server")),
        metrics=metrics,
    )


def _row_is_error(row: Any) -> bool:
    """Whether a single stream row signals a terminal error."""

    if not isinstance(row, dict):
        return False
    if row.get("level") == _ERROR_LEVEL or "error" in row:
        return True
    return ARSpeedTestEventType.from_value(row.get("type")) is (
        ARSpeedTestEventType.ERROR
    )


def stream_has_error(events: Any) -> bool:
    """Whether the stream reports a terminal error (bad server, disconnect)."""

    if not isinstance(events, list):
        return False
    return any(_row_is_error(row) for row in events)


def stream_error_message(events: Any) -> str | None:
    """Return the first error message in the stream, if any."""

    if not isinstance(events, list):
        return None
    for row in events:
        # _row_is_error is only true for dict rows
        if _row_is_error(row):
            message = row.get("message") or row.get("error")
            return raw_to_str(message) if message is not None else None
    return None


def result_server_id(raw_result: Any) -> str | None:
    """Return the normalized server id of a raw result row, or None."""

    server = raw_result.get("server") if isinstance(raw_result, dict) else None
    if not isinstance(server, dict):
        return None
    return normalize_server_id(server.get("id"))


def raw_result_from_events(events: Any) -> dict[str, Any] | None:
    """Return the raw final `result` row from an Ookla event stream."""

    if not isinstance(events, list):
        return None

    final: dict[str, Any] | None = None
    for row in events:
        if not isinstance(row, dict):
            continue
        if ARSpeedTestEventType.from_value(row.get("type")) is (
            ARSpeedTestEventType.RESULT
        ):
            final = row

    return final


def result_from_events(events: Any) -> ARSpeedTestResult | None:
    """Extract the final result from an Ookla event stream."""

    final = raw_result_from_events(events)
    return result_from_dict(final) if final is not None else None


def history_from_list(data: Any) -> list[ARSpeedTestResult]:
    """Build a history list from stored Ookla result objects."""

    if not isinstance(data, list):
        return []
    return [
        result_from_dict(row) for row in data if isinstance(row, dict) and row
    ]


def servers_from_list(data: Any) -> list[ARSpeedTestServer]:
    """Build a server list from an Ookla server list response."""

    if not isinstance(data, list):
        return []
    return [
        server
        for row in data
        if (server := _server_from_dict(row)) is not None
        and server.name is not None
    ]


__all__ = [
    "EXE_TYPE_LIST",
    "EXE_TYPE_RUN",
    "ARSpeedTestEventType",
    "ARSpeedTestResult",
    "ARSpeedTestServer",
    "ARSpeedTestState",
    "build_history_request",
    "build_run_request",
    "build_start_time_request",
    "history_from_list",
    "normalize_server_id",
    "raw_result_from_events",
    "result_server_id",
    "stream_error_message",
    "stream_has_error",
    "result_from_dict",
    "result_from_events",
    "servers_from_list",
]
