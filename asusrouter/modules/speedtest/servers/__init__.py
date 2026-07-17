"""SpeedTest servers module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.speedtest.servers.source import (
    ARSpeedTestServersSource,
    ARSpeedTestServersSourceUniversal,
    fetch_state,
    translate_state,
)

__all__ = [
    "ARSpeedTestServersSource",
    "ARSpeedTestServersSourceUniversal",
    "fetch_state",
    "translate_state",
]
