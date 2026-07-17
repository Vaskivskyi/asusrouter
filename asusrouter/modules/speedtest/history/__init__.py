"""SpeedTest history module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.speedtest.history.source import (
    MAX_HISTORY,
    ARSpeedTestHistorySource,
    ARSpeedTestHistorySourceUniversal,
    async_latest_for_server,
    async_save_result,
    fetch_state,
    translate_state,
)

__all__ = [
    "ARSpeedTestHistorySource",
    "ARSpeedTestHistorySourceUniversal",
    "MAX_HISTORY",
    "async_latest_for_server",
    "async_save_result",
    "fetch_state",
    "translate_state",
]
