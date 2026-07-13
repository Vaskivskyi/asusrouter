"""SpeedTest module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.speedtest.action import ARSpeedTestAction, run_action
from asusrouter.modules.speedtest.enums import (
    ARSpeedTestCapability,
    ARSpeedTestEventType,
    ARSpeedTestState,
)
from asusrouter.modules.speedtest.history import (
    ARSpeedTestHistorySource,
    ARSpeedTestHistorySourceUniversal,
)
from asusrouter.modules.speedtest.models import (
    ARSpeedTestResult,
    ARSpeedTestServer,
)
from asusrouter.modules.speedtest.servers import (
    ARSpeedTestServersSource,
    ARSpeedTestServersSourceUniversal,
)
from asusrouter.modules.speedtest.source import (
    ARSpeedTestSource,
    ARSpeedTestSourceUniversal,
    get_state,
    translate_state,
)

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
