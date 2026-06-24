"""System status module for AsusRouter."""

from __future__ import annotations

from enum import StrEnum
import time
from typing import Any

from asusrouter.const import (
    AR_CALL_GET_STATE,
    AR_CALL_TRANSLATE_STATE,
    UNKNOWN_MEMBER_STR,
)
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint_v2 import (
    AREndpoint,
    get_endpoint_request_type,
)
from asusrouter.modules.metrics import ARMetricType
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import (
    ARCallableEntry,
    ARCallableRegistry as ARCallReg,
)
from asusrouter.tools.converters_v2.raw import raw_to_int
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.types import ARCallbackType
from asusrouter.tools.writers import dict_to_request

# Diagnostics request constants. A single point is unreliable for nodes
# with sparse history, so a window of points is requested and the newest
# (last) is used. `duration`/`point` ~ seconds per point; 60/30 matches
# the device dashboard and leaves margin for sparse nodes
_DIAG_DB = "sys_detect"
_DIAG_DURATION = 60
_DIAG_POINT = 30
_DIAG_REQUEST_TYPE = get_endpoint_request_type(
    AREndpoint.FETCH_DIAGNOSTICS_DATA
)


class ARSystemType(FromStrMixin, StrEnum):
    """A system component reported in the status."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    CPU = "cpu"
    RAM = "ram"


# Device metric name -> (system type, metric). The response columns and
# the request `content` both follow this order, so they cannot drift
_METRICS: tuple[tuple[str, ARSystemType, ARMetricType], ...] = (
    ("cpu_usage", ARSystemType.CPU, ARMetricType.USAGE),
    ("mem_usage", ARSystemType.RAM, ARMetricType.USAGE),
)
_DIAG_CONTENT = ";".join(name for name, *_ in _METRICS)


class ARSystemStatusSource(ARDataSource):
    """AsusRouter system status data source.

    Optionally targets a specific device by MAC; without a target the
    main router is used. Two instances are equal when they target the
    same MAC, so a fresh instance built from any MAC works as a key.
    """

    def __init__(self, target: Any = None) -> None:
        """Initialize the source with an optional target MAC."""

        super().__init__()

        self._target: MacAddress | None = None
        self.target = target

    @property
    def target(self) -> MacAddress | None:
        """Get the target MAC address."""

        return self._target

    @target.setter
    def target(self, value: Any) -> None:
        """Set the target MAC address."""

        self._target = MacAddress.from_value_safe(value)

    def __eq__(self, other: object) -> bool:
        """Two sources are equal when they target the same MAC."""

        if not isinstance(other, ARSystemStatusSource):
            return NotImplemented
        return self._target == other._target

    def __hash__(self) -> int:
        """Hash by type and target MAC."""

        return hash((type(self), self._target))

    def __repr__(self) -> str:
        """Representation of the system status source."""

        return f"<ARSystemStatusSource target=`{self._target}`>"


# Universal instance - preferred (targets the main router)
ARSystemStatusSourceUniversal: ARSystemStatusSource = ARSystemStatusSource()


def _build_request(mac: MacAddress) -> str:
    """Build the diagnostics request for the given target MAC."""

    return dict_to_request(
        {
            "ts": int(time.time()),
            "duration": _DIAG_DURATION,
            "point": _DIAG_POINT,
            "db": _DIAG_DB,
            "content": _DIAG_CONTENT,
            "filter": f"node_mac>txt>{mac.as_asus()}>0",
        },
        request_type=_DIAG_REQUEST_TYPE,
    )


async def get_state(
    callback: ARCallbackType,
    source: ARSystemStatusSource,
    *,
    identity: ARDeviceIdentity,
    **kwargs: Any,
) -> dict[str, Any]:
    """Fetch raw cpu/ram usage for the target, keyed by MAC."""

    mac = source.target or identity.mac
    if mac is None:
        return {}

    data = await callback(
        endpoint=AREndpoint.FETCH_DIAGNOSTICS_DATA,
        request=_build_request(mac),
    )
    contents = data.get("contents") if isinstance(data, dict) else None
    if not contents:
        return {}

    return {mac.as_asus(): contents}


def translate_state(
    data: dict[str, Any],
    *,
    identity: ARDeviceIdentity,
    **kwargs: Any,
) -> dict[MacAddress, dict[ARSystemType, dict[ARMetricType, Any]]]:
    """Translate raw diagnostics rows to the unified per-MAC format."""

    if not isinstance(data, dict) or not data:
        return {}

    result: dict[MacAddress, dict[ARSystemType, dict[ARMetricType, Any]]] = {}
    for mac_raw, contents in data.items():
        mac = MacAddress.from_value_safe(mac_raw)
        if mac is None or not contents:
            continue

        # Rows are time-ascending; the last one is the most recent
        row = contents[-1]
        status: dict[ARSystemType, dict[ARMetricType, Any]] = {}
        for index, (_, system_type, metric) in enumerate(_METRICS):
            if index >= len(row):
                break
            value = raw_to_int(row[index])
            if value is not None:
                status.setdefault(system_type, {})[metric] = value

        if status:
            result[mac] = status

    return result


calls: dict[str, ARCallableEntry] = {
    AR_CALL_GET_STATE: get_state,
    AR_CALL_TRANSLATE_STATE: translate_state,
}

ARCallReg.register(ARSystemStatusSource, **calls)


__all__ = [
    "ARSystemStatusSource",
    "ARSystemStatusSourceUniversal",
    "ARSystemType",
    "get_state",
    "translate_state",
]
