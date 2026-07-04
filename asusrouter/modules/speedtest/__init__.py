"""SpeedTest module for AsusRouter."""

from __future__ import annotations

import asyncio
from enum import StrEnum
import logging
import time
from typing import Any

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.action import ARAction
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.endpoint_v2.hooks import ARHook, hook_request
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.speedtest.history import (
    ARSpeedTestHistorySource,
    ARSpeedTestHistorySourceUniversal,
    async_latest_for_server,
    async_save_result,
)
from asusrouter.modules.speedtest.models import (
    EXE_TYPE_RUN,
    ARSpeedTestEventType,
    ARSpeedTestResult,
    ARSpeedTestServer,
    ARSpeedTestState,
    build_run_request,
    build_start_time_request,
    normalize_server_id,
    raw_result_from_events,
    result_from_events,
    result_server_id,
    stream_error_message,
    stream_has_error,
)
from asusrouter.modules.speedtest.servers import (
    ARSpeedTestServersSource,
    ARSpeedTestServersSourceUniversal,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.poll import async_poll_until
from asusrouter.tools.types import ARCallbackType

_LOGGER = logging.getLogger(__name__)


class ARSpeedTestCapability(FromStrMixin, StrEnum):
    """SpeedTest capabilities."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    SPEED_10G = "speed_10g"


# Sources and actions


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

    def __eq__(self, other: object) -> bool:
        """Equal by chosen server and interface."""

        if not isinstance(other, ARSpeedTestSource):
            return NotImplemented
        return (self.server_id, self.iface) == (other.server_id, other.iface)

    def __hash__(self) -> int:
        """Hash by type, server, and interface."""

        return hash((type(self), self.server_id, self.iface))


# Universal instance (auto server, WAN) - preferred for a default run
ARSpeedTestSourceUniversal: ARSpeedTestSource = ARSpeedTestSource()


class ARSpeedTestAction(ARAction):
    """Run a speedtest."""

    def __init__(
        self,
        server_id: int | str | None = None,
        iface: str | None = None,
    ) -> None:
        """Initialize the action with an optional server and interface."""

        super().__init__()

        self.server_id = normalize_server_id(server_id)
        self.iface = iface

    def __eq__(self, other: object) -> bool:
        """Equal by chosen server and interface."""

        if not isinstance(other, ARSpeedTestAction):
            return NotImplemented
        return (self.server_id, self.iface) == (other.server_id, other.iface)

    def __hash__(self) -> int:
        """Hash by type, server, and interface."""

        return hash((type(self), self.server_id, self.iface))


# Fetch

# The router needs a moment to enter the running state after the trigger;
# polling sooner still sees the previous state and reads a stale result
_RUN_START_DELAY = 1.0

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
            return None
        action = ARSpeedTestAction(source.server_id, source.iface)
        # Note the current result id, so a stale read is not taken as ours
        prior_id = _result_id(await _async_fetch_events(callback))
        if not await run_action_callback(action):
            _LOGGER.debug("Speedtest run did not start; dropping result")
            return None
        # Give the router a moment to clear the old stream and start running
        await asyncio.sleep(_RUN_START_DELAY)
        events = await _async_wait_result(callback, prior_id)
        if events is None:
            _LOGGER.debug("Speedtest run did not finish; dropping result")
            return None
        if stream_has_error(events):
            _LOGGER.debug(
                "Speedtest run failed: %s",
                stream_error_message(events) or "unknown error",
            )
            return None
        # Persist the fresh run to history, if asked
        if save and not await async_save_result(
            callback, raw_result_from_events(events)
        ):
            _LOGGER.debug("Speedtest result not saved to history")
        return events

    return await _async_bare_read(callback, source)


def translate_state(data: Any, **kwargs: Any) -> ARSpeedTestResult | None:
    """Translate the raw result stream into the final result."""

    return result_from_events(data)


# Action


async def run_action(
    callback: ARCallbackType, action: ARSpeedTestAction, **kwargs: Any
) -> bool:
    """Trigger a speedtest run."""

    await callback(
        endpoint=AREndpoint.SET_SPEEDTEST_START_TIME,
        request=build_start_time_request(int(time.time() * 1000)),
    )
    await callback(
        endpoint=AREndpoint.RUN_SPEEDTEST,
        request=build_run_request(
            EXE_TYPE_RUN, server_id=action.server_id, iface=action.iface
        ),
    )
    return True


# Registration

ARCallReg.register_module(
    ARSpeedTestSource, get_state=get_state, translate_state=translate_state
)
ARCallReg.register_action(ARSpeedTestAction, run_action=run_action)


__all__ = [
    "ARSpeedTestAction",
    "ARSpeedTestCapability",
    "ARSpeedTestEventType",
    "ARSpeedTestHistorySource",
    "ARSpeedTestHistorySourceUniversal",
    "ARSpeedTestResult",
    "ARSpeedTestServer",
    "ARSpeedTestServersSource",
    "ARSpeedTestServersSourceUniversal",
    "ARSpeedTestSource",
    "ARSpeedTestSourceUniversal",
    "ARSpeedTestState",
    "get_state",
    "run_action",
    "translate_state",
]
