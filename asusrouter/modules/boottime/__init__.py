"""Boottime module for AsusRouter."""

from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Any

from asusrouter.const import AR_CALL_GET_STATE, AR_CALL_TRANSLATE_STATE
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.endpoint_v2.hooks import ARHook, hook_request
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import (
    ARCallableEntry,
    ARCallableRegistry as ARCallReg,
)
from asusrouter.tools.converters import safe_datetime
from asusrouter.tools.converters_v2.raw import raw_to_int
from asusrouter.tools.types import ARCallbackType

# Boot times within this many seconds are the same boot (1s counter
# precision jitters); a larger forward jump means an actual reboot
_REBOOT_DELTA_THRESHOLD = 2
_UPTIME_MIN_PARTS = 2


def read_uptime(uptime: str) -> datetime | None:
    """Parse an uptime string (`<when>(<secs> ...)`) into the boot time."""

    parts = uptime.split("(")
    if len(parts) < _UPTIME_MIN_PARTS:
        return None
    match = re.search(r"\d+", parts[1])
    if match is None:
        return None
    seconds = raw_to_int(match.group())
    when = safe_datetime(parts[0])
    if when is None or seconds is None:
        return None
    return when - timedelta(seconds=seconds)


class ARBoottimeSource(ARDataSource):
    """Boot time data source for the connected router."""

    def __init__(self) -> None:
        """Initialize the boot time source."""

        super().__init__()

        self._boottime: datetime | None = None

    def __eq__(self, other: object) -> bool:
        """All boot time sources are equal (router-global)."""

        if not isinstance(other, ARBoottimeSource):
            return NotImplemented
        return True

    def __hash__(self) -> int:
        """Hash by type."""

        return hash(type(self))

    def __repr__(self) -> str:
        """Representation of the boot time source."""

        return "<ARBoottimeSource>"

    def stabilize(self, candidate: datetime | None) -> datetime | None:
        """Keep the boot time stable across jitter; update only on reboot."""

        if candidate is None:
            return self._boottime
        prev = self._boottime
        if (
            prev is not None
            and (candidate - prev).total_seconds() < _REBOOT_DELTA_THRESHOLD
        ):
            return prev
        self._boottime = candidate
        return candidate


# Universal instance - preferred
ARBoottimeSourceUniversal: ARBoottimeSource = ARBoottimeSource()


async def get_state(
    callback: ARCallbackType,
    source: ARBoottimeSource,
    **kwargs: Any,
) -> datetime | None:
    """Fetch the uptime hook and return the (stabilized) boot time."""

    raw = await callback(
        endpoint=AREndpoint.FETCH_DATA,
        request=hook_request(ARHook.UPTIME),
    )
    uptime = raw.get("uptime") if isinstance(raw, dict) else None
    candidate = read_uptime(uptime) if isinstance(uptime, str) else None
    return source.stabilize(candidate)


def translate_state(data: Any, **kwargs: Any) -> datetime | None:
    """Pass the boot time through."""

    return data if isinstance(data, datetime) else None


calls: dict[str, ARCallableEntry] = {
    AR_CALL_GET_STATE: get_state,
    AR_CALL_TRANSLATE_STATE: translate_state,
}
ARCallReg.register(ARBoottimeSource, **calls)
