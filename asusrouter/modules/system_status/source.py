"""System status data source for AsusRouter."""

from __future__ import annotations

import time
from typing import Any, NamedTuple

from asusrouter.config.connection import ARConnectionConfigKey as ARCCKey
from asusrouter.modules.common.metrics import ARMetricType
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint_v2 import (
    AREndpoint,
    get_endpoint_request_type,
)
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.system_status import legacy
from asusrouter.modules.system_status.enums import ARSystemType
from asusrouter.modules.system_status.legacy import CpuCounters
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters_v2.raw import raw_to_int
from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.types import ARCallbackType
from asusrouter.tools.writers import dict_to_request

# Diagnostics window: newest of several points (a single point is
# unreliable for sparse nodes); 60/30 matches the device dashboard
_DIAG_DB = "sys_detect"
_DIAG_DURATION = 60
_DIAG_POINT = 30
_DIAG_REQUEST_TYPE = get_endpoint_request_type(
    AREndpoint.FETCH_DIAGNOSTICS_DATA
)

# Highest per-core index reported; extra cores still feed the aggregate
_MAX_CORES = 8


class _LegacyPayload(NamedTuple):
    """Transient legacy cpu/ram transport from get_state to translate."""

    now: CpuCounters
    prev: CpuCounters | None
    ram: dict[ARMetricType, float]


# Core index -> per-core system type
_CORE_TYPES: dict[int, ARSystemType] = {
    index: ARSystemType[f"CORE_{index}"] for index in range(1, _MAX_CORES + 1)
}


# Modern metric name -> (system type, metric), in response/content order
_METRICS: tuple[tuple[str, ARSystemType, ARMetricType], ...] = (
    ("cpu_usage", ARSystemType.CPU, ARMetricType.USAGE),
    ("mem_usage", ARSystemType.RAM, ARMetricType.USAGE),
)
_DIAG_CONTENT = ";".join(name for name, *_ in _METRICS)


class ARSystemStatusSource(ARDataSource):
    """AsusRouter system status data source.

    Optionally targets a device by MAC; without a target the main router
    is used. Instances are equal by target MAC. The pipeline caches one
    instance per target, so the cpu counters stashed here survive across
    refreshes and let the legacy usage be derived statelessly.
    """

    def __init__(self, target: Any = None) -> None:
        """Initialize the source with an optional target MAC."""

        super().__init__()

        self._target: MacAddress | None = None
        self.target = target
        # Previous legacy cpu counters for usage deltas
        self._prev_cpu: CpuCounters | None = None

    @property
    def target(self) -> MacAddress | None:
        """Get the target MAC address."""

        return self._target

    @target.setter
    def target(self, value: Any) -> None:
        """Set the target MAC address."""

        self._target = MacAddress.from_value_safe(value)

    def stash_cpu(self, counters: CpuCounters) -> CpuCounters | None:
        """Store the current cpu counters, returning the previous ones."""

        prev = self._prev_cpu
        self._prev_cpu = counters
        return prev

    def _key(self) -> tuple[Any, ...]:
        """Key by the target MAC."""

        return (self._target,)

    def __repr__(self) -> str:
        """Representation of the system status source."""

        return f"<ARSystemStatusSource target=`{self._target}`>"


# Universal instance - preferred (targets the main router)
ARSystemStatusSourceUniversal: ARSystemStatusSource = ARSystemStatusSource()


def _force_legacy(connection_config: Any) -> bool:
    """Whether the connection config forces the legacy data path."""

    if connection_config is None:
        return False
    try:
        return bool(connection_config.get(ARCCKey.FORCE_LEGACY_SYSTEM_STATUS))
    except KeyError:
        return False


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


async def _get_modern(
    callback: ARCallbackType, mac: MacAddress
) -> dict[str, Any]:
    """Fetch modern diagnostics rows for the target, keyed by MAC."""

    data = await callback(
        endpoint=AREndpoint.FETCH_DIAGNOSTICS_DATA,
        request=_build_request(mac),
    )
    contents = data.get("contents") if isinstance(data, dict) else None
    if not contents:
        return {}

    return {mac.as_asus(): contents}


async def _get_legacy(
    callback: ARCallbackType,
    source: ARSystemStatusSource,
    mac: MacAddress,
    identity: ARDeviceIdentity,
) -> dict[str, Any]:
    """Fetch legacy appGet cpu/ram data for the connected router."""

    # appGet cpu/ram is served only for the connected router, never nodes
    if mac != identity.mac:
        return {}

    data = await callback(
        endpoint=AREndpoint.FETCH_DATA,
        request=legacy.LEGACY_REQUEST,
    )
    if not isinstance(data, dict):
        return {}

    now = legacy.parse_cpu(data.get("cpu_usage") or {})
    ram = legacy.parse_ram(data.get("memory_usage") or {})
    if not now and not ram:
        return {}

    return {mac.as_asus(): _LegacyPayload(now, source.stash_cpu(now), ram)}


async def get_state(
    callback: ARCallbackType,
    source: ARSystemStatusSource,
    *,
    identity: ARDeviceIdentity,
    **kwargs: Any,
) -> dict[str, Any]:
    """Fetch raw cpu/ram data, preferring the modern endpoint.

    Legacy appGet data is calculated and less precise, so it is used only
    when the modern endpoint yields nothing or is forced off.
    """

    mac = source.target or identity.mac
    if mac is None:
        return {}

    if not _force_legacy(kwargs.get("connection_config")):
        modern = await _get_modern(callback, mac)
        if modern:
            return modern

    return await _get_legacy(callback, source, mac, identity)


def _translate_modern(
    rows: list[Any],
) -> dict[ARSystemType, dict[ARMetricType, Any]]:
    """Translate modern diagnostics rows (newest row wins)."""

    row = rows[-1]
    status: dict[ARSystemType, dict[ARMetricType, Any]] = {}
    for index, (_, system_type, metric) in enumerate(_METRICS):
        if index >= len(row):
            break
        value = raw_to_int(row[index])
        if value is not None:
            status.setdefault(system_type, {})[metric] = value

    return status


def _translate_legacy(
    payload: _LegacyPayload,
) -> dict[ARSystemType, dict[ARMetricType, Any]]:
    """Translate legacy cpu/ram payload into the unified format."""

    status: dict[ARSystemType, dict[ARMetricType, Any]] = {}

    aggregate, cores = legacy.translate_cpu(payload.now, payload.prev)
    if aggregate is not None:
        status[ARSystemType.CPU] = {ARMetricType.USAGE: aggregate}
        for core, usage in cores.items():
            core_type = _CORE_TYPES.get(core)
            if core_type is not None:
                status[core_type] = {ARMetricType.USAGE: usage}

    if payload.ram:
        status[ARSystemType.RAM] = dict(payload.ram)

    return status


def translate_state(
    data: dict[str, Any],
    *,
    identity: ARDeviceIdentity,
    **kwargs: Any,
) -> dict[MacAddress, dict[ARSystemType, dict[ARMetricType, Any]]]:
    """Translate raw cpu/ram data to the unified per-MAC format."""

    if not isinstance(data, dict) or not data:
        return {}

    result: dict[MacAddress, dict[ARSystemType, dict[ARMetricType, Any]]] = {}
    for mac_raw, payload in data.items():
        mac = MacAddress.from_value_safe(mac_raw)
        if mac is None or not payload:
            continue

        status = (
            _translate_legacy(payload)
            if isinstance(payload, _LegacyPayload)
            else _translate_modern(payload)
        )
        if status:
            result[mac] = status

    return result


ARCallReg.register_module(
    ARSystemStatusSource, get_state=get_state, translate_state=translate_state
)


__all__ = [
    "ARSystemStatusSource",
    "ARSystemStatusSourceUniversal",
    "get_state",
    "translate_state",
]
