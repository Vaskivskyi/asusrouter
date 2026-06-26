"""Interface Traffic module for AsusRouter."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from asusrouter.const import AR_CALL_GET_STATE, AR_CALL_TRANSLATE_STATE
from asusrouter.error import AsusRouter404Error
from asusrouter.modules.common.metrics import ARMetricType
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint_v2 import (
    AREndpoint,
    get_endpoint_request_type,
)
from asusrouter.modules.endpoint_v2.hooks import ARHook, hook_request
from asusrouter.modules.traffic.base import (
    ARTrafficLink,
    ARTrafficSource,
    ARTrafficType,
)
from asusrouter.modules.wifi import ARWiFiBand
from asusrouter.registry import (
    ARCallableEntry,
    ARCallableRegistry as ARCallReg,
)
from asusrouter.tools.converters_v2.raw import raw_to_int
from asusrouter.tools.readers_v2 import read_netdev
from asusrouter.tools.types import ARCallbackType
from asusrouter.tools.writers import dict_to_request

# Legacy appGet hook that yields the same `netdev` payload
_APPGET_NETDEV_REQUEST = hook_request((ARHook.NETDEV, "appobj"))

# Bits per byte, for byte-counter delta -> bit rate
_BITS_PER_BYTE = 8

# Shortest interval that yields a meaningful speed; below it, report 0
_MIN_DELTA_TIME = 1.0

# Raw interface name -> fixed traffic type
_STATIC_MAP: dict[str, ARTrafficType] = {
    "INTERNET": ARTrafficType.WAN,
    "INTERNET1": ARTrafficType.USB,
    "WIRED": ARTrafficType.WIRED,
    "BRIDGE": ARTrafficType.BRIDGE,
    "LACP1": ARTrafficType.LACP1,
    "LACP2": ARTrafficType.LACP2,
}

_WIRELESS_PREFIX = "WIRELESS"

# Interfaces summed into the cumulative LACP link
_LACP_PARTS = ("LACP1", "LACP2")

_Counters = dict[str, dict[str, int]]


class ARTrafficInterfaceSource(ARTrafficSource):
    """Interface traffic source for the connected router.

    A single fetch returns every available interface, so there is no
    per-link variant; the previous sample is stashed here for speeds.
    """

    def __init__(self, target: Any = None) -> None:
        """Initialize the interface traffic source."""

        super().__init__(link=None, target=target)

        self._prev: _Counters | None = None
        self._prev_ts: datetime | None = None

    def stash(
        self, counters: _Counters, timestamp: datetime
    ) -> tuple[_Counters | None, datetime | None]:
        """Store the latest sample and return the previous one."""

        prev, prev_ts = self._prev, self._prev_ts
        self._prev, self._prev_ts = counters, timestamp
        return prev, prev_ts


async def _fetch(
    callback: ARCallbackType,
    raw_callback: ARCallbackType | None,
) -> _Counters:
    """Fetch counters from `update.cgi`, falling back to appGet.

    The fallback reads the raw appGet content (not the shared JSON reader,
    which would collapse the dual-WAN duplicates) and runs it through the
    same netdev parser, so duplicates are summed in both paths.
    """

    request = dict_to_request(
        {"output": "netdev"},
        request_type=get_endpoint_request_type(AREndpoint.FETCH_UPDATE),
    )
    try:
        modern = await callback(
            endpoint=AREndpoint.FETCH_UPDATE, request=request
        )
    except AsusRouter404Error:
        modern = None
    if isinstance(modern, dict) and modern:
        return modern

    if raw_callback is None:
        return {}
    legacy = await raw_callback(
        endpoint=AREndpoint.FETCH_DATA, request=_APPGET_NETDEV_REQUEST
    )
    return read_netdev(legacy) if isinstance(legacy, str) else {}


async def get_state(
    callback: ARCallbackType,
    source: ARTrafficInterfaceSource,
    *,
    identity: ARDeviceIdentity | None = None,
    raw_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Fetch interface counters and stash them for the next speed delta."""

    now = await _fetch(callback, raw_callback)
    now_ts = datetime.now(UTC)
    prev, prev_ts = source.stash(now, now_ts)
    delta_time = (
        (now_ts - prev_ts).total_seconds() if prev_ts is not None else None
    )
    return {"now": now, "prev": prev, "delta_time": delta_time}


def _invert_wifi(identity: ARDeviceIdentity | None) -> dict[int, ARWiFiBand]:
    """Map a wireless unit index to its band via the identity."""

    if identity is None:
        return {}
    return {unit: band for band, unit in identity.wifi.items()}


def _map_iface(
    iface: str, wifi: dict[int, ARWiFiBand]
) -> ARTrafficLink | None:
    """Resolve a raw interface name to its traffic link, or None."""

    fixed = _STATIC_MAP.get(iface)
    if fixed is not None:
        return fixed
    if iface.startswith(_WIRELESS_PREFIX):
        unit = raw_to_int(iface[len(_WIRELESS_PREFIX) :])
        return wifi.get(unit) if unit is not None else None
    return None


def _speed(
    value: int,
    prev: dict[str, int] | None,
    kind: str,
    delta_time: float | None,
) -> float:
    """Bit rate from the counter delta, or 0 when not measurable.

    Returns 0 without a previous sample, for intervals shorter than a
    second (too short to be meaningful) and for negative deltas (the
    counter wrapped or reset on the device).
    """

    if prev is None or delta_time is None or delta_time < _MIN_DELTA_TIME:
        return 0.0
    previous = prev.get(kind)
    if previous is None:
        return 0.0
    delta = value - previous
    return _BITS_PER_BYTE * delta / delta_time if delta >= 0 else 0.0


def _metrics(
    now: dict[str, int],
    prev: dict[str, int] | None,
    delta_time: float | None,
) -> dict[ARMetricType, Any]:
    """Build counter and speed metrics for one interface."""

    counters = {"rx": ARMetricType.RX, "tx": ARMetricType.TX}
    speeds = {"rx": ARMetricType.RX_SPEED, "tx": ARMetricType.TX_SPEED}

    result: dict[ARMetricType, Any] = {}
    for kind, metric in counters.items():
        value = now.get(kind)
        if value is None:
            continue
        result[metric] = value
        result[speeds[kind]] = _speed(value, prev, kind, delta_time)
    return result


def _sum_counters(counters: _Counters | None, parts: tuple[str, ...]) -> Any:
    """Sum byte counters across the given interfaces, or None if absent."""

    present = [counters[p] for p in parts if counters and p in counters]
    if not present:
        return None
    return {
        kind: sum(c[kind] for c in present if kind in c)
        for kind in ("rx", "tx")
        if any(kind in c for c in present)
    }


def translate_state(
    data: Any,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[ARTrafficLink, Any]:
    """Translate counters into the flat per-link traffic metrics."""

    if not isinstance(data, dict):
        return {}

    now: _Counters = data.get("now") or {}
    prev: _Counters | None = data.get("prev")
    delta_time: float | None = data.get("delta_time")
    wifi = _invert_wifi(identity)

    result: dict[ARTrafficLink, Any] = {}
    for iface, counters in now.items():
        link = _map_iface(iface, wifi)
        if link is None:
            continue
        prev_iface = prev.get(iface) if prev else None
        result[link] = _metrics(counters, prev_iface, delta_time)

    # Cumulative LACP from its physical members
    lacp_now = _sum_counters(now, _LACP_PARTS)
    if lacp_now is not None:
        result[ARTrafficType.LACP] = _metrics(
            lacp_now, _sum_counters(prev, _LACP_PARTS), delta_time
        )

    return result


calls: dict[str, ARCallableEntry] = {
    AR_CALL_GET_STATE: get_state,
    AR_CALL_TRANSLATE_STATE: translate_state,
}
ARCallReg.register(ARTrafficInterfaceSource, **calls)
