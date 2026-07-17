"""SpeedTest history data source for AsusRouter."""

from __future__ import annotations

import logging
from typing import Any

from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.endpoint.hooks import ARHook, hook_request, hook_value
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.speedtest.models import (
    ARSpeedTestResult,
    build_history_request,
    history_from_list,
    result_server_id,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.types import ARCallbackType

_LOGGER = logging.getLogger(__name__)

_HISTORY_REQUEST = hook_request(ARHook.OOKLA_SPEEDTEST_HISTORY)

# The WebUI trims stored history to the newest entries
MAX_HISTORY = 50


# Sources and actions


class ARSpeedTestHistorySource(ARDataSource):
    """AsusRouter speedtest history data source (read-only)."""


# Universal instance - preferred
ARSpeedTestHistorySourceUniversal: ARSpeedTestHistorySource = (
    ARSpeedTestHistorySource()
)


# Fetch


async def _async_fetch_history(callback: ARCallbackType) -> Any:
    """Fetch the raw speedtest history."""

    data = await callback(
        endpoint=AREndpoint.FETCH_DATA, request=_HISTORY_REQUEST
    )
    return hook_value(data, ARHook.OOKLA_SPEEDTEST_HISTORY)


async def fetch_state(
    callback: ARCallbackType,
    source: ARSpeedTestHistorySource,
    **kwargs: Any,
) -> Any:
    """Fetch the raw speedtest history."""

    history = await _async_fetch_history(callback)
    return history if history is not None else {}


def translate_state(data: Any, **kwargs: Any) -> list[ARSpeedTestResult]:
    """Translate the raw history into results."""

    return history_from_list(data)


async def async_latest_for_server(
    callback: ARCallbackType, server_id: str
) -> dict[str, Any] | None:
    """Return the newest stored raw result run against the given server."""

    current = await _async_fetch_history(callback)
    if not isinstance(current, list):
        return None
    # History is newest-first, so the first match is the latest run
    for entry in current:
        if isinstance(entry, dict) and result_server_id(entry) == server_id:
            return entry
    return None


# Save


def _entry_id(entry: Any) -> str | None:
    """Return the `result.id` of a stored history entry, or None."""

    result = entry.get("result") if isinstance(entry, dict) else None
    return result.get("id") if isinstance(result, dict) else None


async def async_save_result(
    callback: ARCallbackType, new_raw: dict[str, Any] | None
) -> bool:
    """Append a fresh run to stored history, deduped by result id."""

    new_id = _entry_id(new_raw)
    if new_raw is None or new_id is None:
        _LOGGER.debug("Result has no id; not saving to history")
        return False

    current = await _async_fetch_history(callback)
    existing = (
        [entry for entry in current if isinstance(entry, dict) and entry]
        if isinstance(current, list)
        else []
    )
    if any(_entry_id(entry) == new_id for entry in existing):
        _LOGGER.debug("Result %s already in history; skipping write", new_id)
        return True

    entries = [new_raw, *existing][:MAX_HISTORY]
    await callback(
        endpoint=AREndpoint.WRITE_SPEEDTEST_HISTORY,
        request=build_history_request(entries),
    )
    return True


# Registration

ARCallReg.register_source(
    ARSpeedTestHistorySource,
    fetch_state=fetch_state,
    translate_state=translate_state,
)


__all__ = [
    "ARSpeedTestHistorySource",
    "ARSpeedTestHistorySourceUniversal",
    "async_latest_for_server",
    "async_save_result",
    "fetch_state",
    "translate_state",
]
