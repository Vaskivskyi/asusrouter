"""SpeedTest data source for AsusRouter."""

from __future__ import annotations

import logging
from typing import Any

from asusrouter.modules.action import async_start_run
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.endpoint_v2.hooks import ARHook, hook_request
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.speedtest.action import ARSpeedTestAction
from asusrouter.modules.speedtest.history import (
    async_latest_for_server,
    async_save_result,
)
from asusrouter.modules.speedtest.models import (
    ARSpeedTestResult,
    normalize_server_id,
    raw_result_from_events,
    result_from_events,
    result_server_id,
    stream_error_message,
    stream_has_error,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.poll import async_poll_until
from asusrouter.tools.types import ARCallbackType

_LOGGER = logging.getLogger(__name__)


class ARSpeedTestSource(ARDataSource):
    """AsusRouter speedtest data source."""

    def __init__(
        self,
        server_id: int | str | None = None,
        iface: str | None = None,
    ) -> None:
        """Initialize the source with an optional server and interface."""

        super().__init__()

        self.server_id = normalize_server_id(server_id)
        self.iface = iface

    def _key(self) -> tuple[Any, ...]:
        """Key by the chosen server and interface."""

        return (self.server_id, self.iface)


# Universal instance (auto server, WAN) - preferred for a default run
ARSpeedTestSourceUniversal: ARSpeedTestSource = ARSpeedTestSource()


# Fetch

# Wait out a run before reading; the WebUI caps a test at 120s
_POLL_INTERVAL = 2.0
_POLL_ATTEMPTS = 90

_RESULT_REQUEST = hook_request(ARHook.OOKLA_SPEEDTEST_RESULT)


def _extract(data: Any) -> Any:
    """Pull the result stream out of a hook response."""

    if isinstance(data, dict):
        return data.get(ARHook.OOKLA_SPEEDTEST_RESULT.value)
    return None


async def _async_fetch_events(callback: ARCallbackType) -> Any:
    """Fetch the raw Ookla result stream."""

    data = await callback(
        endpoint=AREndpoint.FETCH_DATA, request=_RESULT_REQUEST
    )
    return _extract(data)


def _result_id(events: Any) -> str | None:
    """Return the id of the final result row, or None if there is none yet."""

    raw = raw_result_from_events(events)
    result = raw.get("result") if isinstance(raw, dict) else None
    return result.get("id") if isinstance(result, dict) else None


def _log_stream(events: Any) -> None:
    """Log the stream length and the last typed row, for live diagnosis."""

    # Skip the stream walk entirely when debug logging is off
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return

    if not isinstance(events, list):
        # Do not dump the payload - its contents are unknown and may be
        # sensitive; the type alone is enough to diagnose
        _LOGGER.debug(
            "Speedtest stream: not a list (type=%s)", type(events).__name__
        )
        return

    last_type: Any = None
    for row in reversed(events):
        if isinstance(row, dict) and row.get("type"):
            last_type = row.get("type")
            break

    _LOGGER.debug(
        "Speedtest stream: %d items, last type=%s, result id=%s",
        len(events),
        last_type,
        _result_id(events),
    )


async def _async_wait_result(
    callback: ARCallbackType, prior_id: str | None
) -> Any:
    """Poll the result stream until a fresh completed result appears."""

    async def _probe(**kwargs: Any) -> Any:
        events = await _async_fetch_events(callback)
        _log_stream(events)
        return events

    def _ready(events: Any) -> bool:
        # Stop early on a terminal error (bad server, disconnect)
        if stream_has_error(events):
            return True
        rid = _result_id(events)
        return rid is not None and rid != prior_id

    return await async_poll_until(
        _probe,
        _ready,
        interval=_POLL_INTERVAL,
        attempts=_POLL_ATTEMPTS,
    )


async def _async_bare_read(
    callback: ARCallbackType, source: ARSpeedTestSource
) -> Any:
    """Read the last result."""

    events = await _async_fetch_events(callback)
    if source.server_id is None:
        return events

    last = raw_result_from_events(events)
    if last is not None and result_server_id(last) == source.server_id:
        return events

    # The last run was for another server; fall back to stored history
    stored = await async_latest_for_server(callback, source.server_id)
    return [stored] if stored is not None else None


async def get_state(
    callback: ARCallbackType,
    source: ARSpeedTestSource,
    *,
    run_action_callback: ARCallbackType | None = None,
    refresh: bool = False,
    save: bool = False,
    **kwargs: Any,
) -> Any:
    """Fetch the last speedtest result."""

    # Optionally trigger a fresh run against the source's server/interface
    if refresh:
        if run_action_callback is None:
            return {}
        action = ARSpeedTestAction(source.server_id, source.iface)
        # Note the current result id, so a stale read is not taken as ours
        prior_id = _result_id(await _async_fetch_events(callback))
        if not await async_start_run(run_action_callback, action):
            return {}
        events = await _async_wait_result(callback, prior_id)
        if events is None:
            _LOGGER.debug("Speedtest run did not finish; dropping result")
            return {}
        if stream_has_error(events):
            _LOGGER.debug(
                "Speedtest run failed: %s",
                stream_error_message(events) or "unknown error",
            )
            return {}
        # Persist the fresh run to history, if asked
        if save and not await async_save_result(
            callback, raw_result_from_events(events)
        ):
            _LOGGER.debug("Speedtest result not saved to history")
        return events

    result = await _async_bare_read(callback, source)
    return result if result is not None else {}


def translate_state(data: Any, **kwargs: Any) -> ARSpeedTestResult | None:
    """Translate the raw result stream into the final result."""

    return result_from_events(data)


# Registration

ARCallReg.register_module(
    ARSpeedTestSource, get_state=get_state, translate_state=translate_state
)


__all__ = [
    "ARSpeedTestSource",
    "ARSpeedTestSourceUniversal",
    "get_state",
    "translate_state",
]
