"""Clock data source for AsusRouter."""

from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Any, Self

from asusrouter.modules.clock.enums import ARClockField
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.endpoint.hooks import ARHook, hook_request
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters.raw import raw_to_datetime
from asusrouter.tools.types import ARCallbackType

# Boot times within this many seconds are the same boot (1s counter
# precision jitters); a larger forward jump means an actual reboot
_REBOOT_DELTA_THRESHOLD = 2
_UPTIME_MIN_PARTS = 2

# Consider no device online more than 100 years. If so, reboot it right away
_UPTIME_MAX_SECONDS = 100 * 365 * 24 * 3600

# Old firmware returns the uptime hook as invalid JSON (the value is not
# quoted), so the JSON reader drops it - pull it out of the raw content
_UPTIME_RE = re.compile(r'"uptime"\s*:\s*([^}\n]+)')

# The seconds-since-boot count, inside the parenthesised tail
_SECONDS_RE = re.compile(r"\d+")


def _extract_uptime(content: Any) -> str | None:
    """Extract the uptime value from a raw (possibly non-JSON) response."""

    if not isinstance(content, str):
        return None
    match = _UPTIME_RE.search(content)
    if match is None:
        return None
    return match.group(1).strip().strip('"') or None


class ARBoottime(datetime):
    """Boot time - a datetime tagged so the identity sync is unambiguous."""

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        """Build a boot time, rejecting one that states no offset."""

        value = super().__new__(cls, *args, **kwargs)
        if value.tzinfo is None:
            raise ValueError("a boot time must state its offset")

        return value

    @classmethod
    def from_datetime(cls, value: datetime) -> ARBoottime:
        """Build a boot time from a plain datetime."""

        return cls(
            value.year,
            value.month,
            value.day,
            value.hour,
            value.minute,
            value.second,
            value.microsecond,
            value.tzinfo,
            fold=value.fold,
        )


def _as_boottime(value: datetime | None) -> ARBoottime | None:
    """Tag a datetime as a boot time (None passes through)."""

    if value is None or isinstance(value, ARBoottime):
        return value
    return ARBoottime.from_datetime(value)


def read_uptime(uptime: str) -> dict[ARClockField, Any]:
    """Read an uptime string (`<when>(<secs> ...)`) into what it states."""

    parts = uptime.split("(", 1)
    if len(parts) < _UPTIME_MIN_PARTS:
        return {}
    match = _SECONDS_RE.search(parts[1])
    if match is None:
        return {}
    # The match is digits only
    seconds = int(match.group())
    if seconds > _UPTIME_MAX_SECONDS:
        return {}

    when = raw_to_datetime(parts[0])
    # A clock that does not state its offset is not a clock
    if when is None or when.tzinfo is None:
        return {ARClockField.UPTIME: seconds}

    try:
        boottime = _as_boottime(when - timedelta(seconds=seconds))
    except OverflowError:
        # A clock this early cannot have been running that long
        return {ARClockField.UPTIME: seconds}

    return {
        ARClockField.BOOTTIME: boottime,
        ARClockField.DEVICE_TIME: when,
        ARClockField.UPTIME: seconds,
    }


def _aware(value: datetime | None) -> datetime | None:
    """Drop a datetime that states no offset."""

    return value if value is not None and value.tzinfo is not None else None


def stabilize(
    candidate: datetime | None, prev: datetime | None
) -> ARBoottime | None:
    """Keep the boot time stable across jitter; update only on reboot."""

    candidate = _aware(candidate)
    prev = _aware(prev)

    if candidate is None:
        return _as_boottime(prev)
    if (
        prev is not None
        and (candidate - prev).total_seconds() < _REBOOT_DELTA_THRESHOLD
    ):
        return _as_boottime(prev)
    return _as_boottime(candidate)


class ARClockSource(ARDataSource):
    """Clock data source for the connected router."""


# Universal instance - preferred
ARClockSourceUniversal: ARClockSource = ARClockSource()


async def fetch_state(
    callback: ARCallbackType,
    source: ARClockSource,
    *,
    identity: ARDeviceIdentity | None = None,
    fetch_raw_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> dict[ARClockField, Any]:
    """Fetch the uptime hook and read the device's clock out of it."""

    request = hook_request(ARHook.UPTIME)

    # Prefer the raw content: the uptime value is not valid JSON on old
    # firmware, so the JSON reader would log a spurious decode error
    uptime: str | None = None
    if fetch_raw_callback is not None:
        content = await fetch_raw_callback(
            endpoint=AREndpoint.FETCH_DATA, request=request
        )
        uptime = _extract_uptime(content)

    if uptime is None:
        raw = await callback(endpoint=AREndpoint.FETCH_DATA, request=request)
        value = raw.get("uptime") if isinstance(raw, dict) else None
        uptime = value if isinstance(value, str) else None

    state = read_uptime(uptime) if uptime is not None else {}

    # Only the boot time is stabilized
    prev = identity.boottime if identity is not None else None
    boottime = stabilize(state.get(ARClockField.BOOTTIME), prev)
    if boottime is not None:
        state[ARClockField.BOOTTIME] = boottime

    return state


ARCallReg.register_source(ARClockSource, fetch_state=fetch_state)


__all__ = [
    "ARBoottime",
    "ARClockSource",
    "ARClockSourceUniversal",
    "fetch_state",
    "read_uptime",
    "stabilize",
]
