"""Ping data source for AsusRouter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import logging
from typing import Any

from asusrouter.modules.action import async_start_run
from asusrouter.modules.common.metrics import ARMetricType
from asusrouter.modules.endpoint_v2 import (
    AREndpoint,
    get_endpoint_request_type,
)
from asusrouter.modules.nvram import ARNvramType, async_get_value
from asusrouter.modules.ping.action import ARPingAction
from asusrouter.modules.ping.enums import ARPingStatus
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters_v2.raw import (
    raw_to_bool,
    raw_to_float,
    raw_to_int,
    raw_to_str,
)
from asusrouter.tools.identifiers.ip import IpAddress
from asusrouter.tools.poll import async_poll_until
from asusrouter.tools.types import ARCallbackType
from asusrouter.tools.writers import dict_to_request

_LOGGER = logging.getLogger(__name__)


# Data model


@dataclass
class ARPingResult:
    """Ping result for a single target."""

    alias: str | None = None
    valid: bool | None = None
    timestamp: int | None = None
    metrics: dict[ARMetricType, float | int] = field(default_factory=dict)


# Source


class ARPingSource(ARDataSource):
    """AsusRouter ping data source."""


# Universal instance - preferred
ARPingSourceUniversal: ARPingSource = ARPingSource()


# Fetch

# Diagnostics db holding the last ping run results
_DIAG_DB = "dns_ping"
_DIAG_REQUEST_TYPE = get_endpoint_request_type(
    AREndpoint.FETCH_DIAGNOSTICS_DATA
)

# Poll dns_ping_state until the run finishes before reading results,
# otherwise the router may return empty or partial rows
_POLL_INTERVAL = 1.0
_POLL_ATTEMPTS = 15

# Diagnostics content columns, in request/response order
_CONTENT_COLUMNS = (
    "dns_ip",
    "alias",
    "valid",
    "min",
    "avg",
    "max",
    "pkt_sent",
    "pkt_recv",
    "pkt_loss_rate",
    "data_time",
)
_DIAG_CONTENT = ";".join(_CONTENT_COLUMNS)

# Column name -> index in the response row
_COL = {name: index for index, name in enumerate(_CONTENT_COLUMNS)}

# Metric column name -> (metric, converter); latency stored in ms
# ms as base units for ping
_METRIC_COLUMNS: tuple[tuple[str, ARMetricType, Any], ...] = (
    ("min", ARMetricType.LATENCY_MIN, raw_to_float),
    ("avg", ARMetricType.LATENCY_AVG, raw_to_float),
    ("max", ARMetricType.LATENCY_MAX, raw_to_float),
    ("pkt_sent", ARMetricType.PACKETS_SENT, raw_to_int),
    ("pkt_recv", ARMetricType.PACKETS_RECEIVED, raw_to_int),
    ("pkt_loss_rate", ARMetricType.PACKET_LOSS, raw_to_float),
)


def _build_request() -> str:
    """Build the diagnostics request for ping results."""

    return dict_to_request(
        {"db": _DIAG_DB, "content": _DIAG_CONTENT},
        request_type=_DIAG_REQUEST_TYPE,
    )


async def _async_wait_finished(get_data_callback: ARCallbackType) -> bool:
    """Poll `dns_ping_state` until the ping run reports finished."""

    async def _probe(**kwargs: Any) -> ARPingStatus:
        raw = await async_get_value(
            get_data_callback, ARNvramType.DNS_PING_STATUS, **kwargs
        )
        return ARPingStatus.from_value(raw)

    # Force each poll to bypass the state cache, so we see fresh status
    status = await async_poll_until(
        _probe,
        lambda value: value is ARPingStatus.FINISHED,
        interval=_POLL_INTERVAL,
        attempts=_POLL_ATTEMPTS,
        force=True,
    )
    return status is ARPingStatus.FINISHED


async def get_state(
    callback: ARCallbackType,
    source: ARPingSource,
    *,
    get_data_callback: ARCallbackType | None = None,
    run_action_callback: ARCallbackType | None = None,
    refresh: bool = False,
    **kwargs: Any,
) -> Any:
    """Fetch ping results; with `refresh`, run a fresh ping first."""

    if get_data_callback is None:
        return {}

    # Optionally trigger a fresh run
    if refresh and not await async_start_run(
        run_action_callback, ARPingAction()
    ):
        return {}

    # A run may be in progress (ours or an unrelated trigger); wait it out
    # before reading, or drop stale/partial data
    if not await _async_wait_finished(get_data_callback):
        _LOGGER.debug("Ping run did not finish; dropping results")
        return {}

    data = await callback(
        endpoint=AREndpoint.FETCH_DIAGNOSTICS_DATA,
        request=_build_request(),
    )
    contents = data.get("contents") if isinstance(data, dict) else None
    if not contents:
        return {}

    return contents


def _read(row: list[Any], name: str, converter: Callable[[Any], Any]) -> Any:
    """Convert the named column of a row, or None if absent."""

    index = _COL[name]
    return converter(row[index]) if index < len(row) else None


def _translate_row(row: list[Any]) -> ARPingResult:
    """Translate a single ping row into an `ARPingResult`."""

    metrics: dict[ARMetricType, float | int] = {}
    for name, metric, converter in _METRIC_COLUMNS:
        value = _read(row, name, converter)
        if value is not None:
            metrics[metric] = value

    return ARPingResult(
        alias=_read(row, "alias", raw_to_str),
        valid=_read(row, "valid", raw_to_bool),
        timestamp=_read(row, "data_time", raw_to_int),
        metrics=metrics,
    )


def translate_state(data: Any, **kwargs: Any) -> dict[IpAddress, ARPingResult]:
    """Translate raw ping rows into per-target results, keyed by IP."""

    if not isinstance(data, list):
        return {}

    result: dict[IpAddress, ARPingResult] = {}
    for row in data:
        if not isinstance(row, (list, tuple)) or not row:
            continue
        ip = IpAddress.from_value_safe(row[0])
        if ip is None:
            continue
        result[ip] = _translate_row(list(row))

    return result


# Registration

ARCallReg.register_module(
    ARPingSource, get_state=get_state, translate_state=translate_state
)


__all__ = [
    "ARPingResult",
    "ARPingSource",
    "ARPingSourceUniversal",
    "get_state",
    "translate_state",
]
