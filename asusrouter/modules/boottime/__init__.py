"""Boottime module for AsusRouter."""

from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Any

from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.endpoint_v2.hooks import ARHook, hook_request
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters import safe_datetime
from asusrouter.tools.converters_v2.raw import raw_to_int
from asusrouter.tools.types import ARCallbackType

# Boot times within this many seconds are the same boot (1s counter
# precision jitters); a larger forward jump means an actual reboot
_REBOOT_DELTA_THRESHOLD = 2
_UPTIME_MIN_PARTS = 2


class ARBoottime(datetime):
    """Boot time - a datetime tagged so the identity sync is unambiguous."""

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


def read_uptime(uptime: str) -> ARBoottime | None:
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
    return _as_boottime(when - timedelta(seconds=seconds))


def stabilize(
    candidate: datetime | None, prev: datetime | None
) -> ARBoottime | None:
    """Keep the boot time stable across jitter; update only on reboot."""

    if candidate is None:
        return _as_boottime(prev)
    if (
        prev is not None
        and (candidate - prev).total_seconds() < _REBOOT_DELTA_THRESHOLD
    ):
        return _as_boottime(prev)
    return _as_boottime(candidate)


class ARBoottimeSource(ARDataSource):
    """Boot time data source for the connected router."""


# Universal instance - preferred
ARBoottimeSourceUniversal: ARBoottimeSource = ARBoottimeSource()


async def get_state(
    callback: ARCallbackType,
    source: ARBoottimeSource,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> ARBoottime | None:
    """Fetch the uptime hook and return the (stabilized) boot time."""

    raw = await callback(
        endpoint=AREndpoint.FETCH_DATA,
        request=hook_request(ARHook.UPTIME),
    )
    uptime = raw.get("uptime") if isinstance(raw, dict) else None
    candidate = read_uptime(uptime) if isinstance(uptime, str) else None
    prev = identity.boottime if identity is not None else None
    return stabilize(candidate, prev)


ARCallReg.register_module(ARBoottimeSource, get_state=get_state)
