"""SysInfo data source for AsusRouter (Merlin firmware only)."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity

from asusrouter.modules.common.metrics import ARMetricType
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.sysinfo.enums import (
    ARMemoryType,
    ARSysInfoType,
    ARWlanClientCount,
)
from asusrouter.modules.wifi import AR_WIFI_UNIT_FALLBACK, ARWiFiBand
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters.raw import raw_to_float, raw_to_int
from asusrouter.tools.types import ARCallbackType
from asusrouter.tools.units import DataUnitConverter, UnitOfData

_K = TypeVar("_K")
_V = TypeVar("_V")

# Merlin reports memory and JFFS in decimal MB; NVRAM in bytes
_megabytes_to_bytes = DataUnitConverter.converter_factory(
    UnitOfData.MEGABYTE, UnitOfData.BYTE
)

# Load average windows in minutes, in `cpu_stats_arr` order
_LOAD_AVERAGE_WINDOWS: tuple[int, ...] = (1, 5, 15)


# Client counts in `wlc_{i}_arr` order
_WLAN_CLIENT_ORDER: tuple[ARWlanClientCount, ...] = (
    ARWlanClientCount.ASSOCIATED,
    ARWlanClientCount.AUTHORIZED,
    ARWlanClientCount.AUTHENTICATED,
)

# Connection counts in `conn_stats_arr` order
_CONNECTION_ORDER: tuple[ARMetricType, ...] = (
    ARMetricType.TOTAL,
    ARMetricType.ACTIVE,
)

# MB memory fields by `mem_stats_arr` index; USED/AVAILABLE only from 388.7
_MEMORY_MB_FIELDS: dict[int, ARMemoryType] = {
    0: ARMemoryType.TOTAL,
    1: ARMemoryType.FREE,
    2: ARMemoryType.BUFFERS,
    3: ARMemoryType.CACHE,
    4: ARMemoryType.SWAP_USED,
    5: ARMemoryType.SWAP_TOTAL,
    8: ARMemoryType.USED,
    9: ARMemoryType.AVAILABLE,
}
# Index of the NVRAM value (already in bytes) in `mem_stats_arr`
_MEMORY_NVRAM_INDEX = 6
# Index of the JFFS value in `mem_stats_arr`
_MEMORY_JFFS_INDEX = 7


def _mb_to_bytes(value: Any) -> int | None:
    """Convert a raw MB value to bytes, or None."""

    megabytes = raw_to_float(value)
    if megabytes is None:
        return None
    return round(_megabytes_to_bytes(megabytes))


def _map_positional(
    raw: Sequence[Any],
    fields: Iterable[tuple[int, _K]],
    convert: Callable[[Any], _V | None],
) -> dict[_K, _V]:
    """Map raw values at given indices onto keys, skipping gaps and None."""

    result: dict[_K, _V] = {}
    for index, key in fields:
        if index >= len(raw):
            continue
        value = convert(raw[index])
        if value is not None:
            result[key] = value

    return result


def _wlan_index_to_band(
    identity: ARDeviceIdentity | None,
) -> dict[int, ARWiFiBand]:
    """Resolve `wlc` index -> band, preferring `identity.wifi`."""

    if identity is not None and identity.wifi:
        return identity.wifi_by_unit
    return AR_WIFI_UNIT_FALLBACK


def _translate_wlan(
    data: dict[str, Any],
    index_to_band: dict[int, ARWiFiBand],
) -> dict[ARWiFiBand, dict[ARWlanClientCount, int]]:
    """Translate per-band wireless client counts."""

    wlan: dict[ARWiFiBand, dict[ARWlanClientCount, int]] = {}

    index = 0
    while (raw := data.get(f"wlc_{index}_arr")) is not None:
        band = index_to_band.get(index, ARWiFiBand.UNKNOWN)
        wlan[band] = _map_positional(
            raw, enumerate(_WLAN_CLIENT_ORDER), raw_to_int
        )
        index += 1

    return wlan


def _translate_connections(data: dict[str, Any]) -> dict[ARMetricType, int]:
    """Translate total and active connection counts."""

    raw = data.get("conn_stats_arr") or ()
    return _map_positional(raw, enumerate(_CONNECTION_ORDER), raw_to_int)


def _translate_jffs(value: str) -> dict[ARMemoryType, int]:
    """Translate the JFFS value in both reporting formats."""

    jffs: dict[ARMemoryType, int] = {}

    # Before 388.7: `XX.xx / YY.yy MB` (used / total)
    used_str, sep, total_str = value.partition("/")
    if sep:
        used = _mb_to_bytes(used_str)
        total = _mb_to_bytes(total_str.removesuffix(" MB"))
        if used is not None:
            jffs[ARMemoryType.JFFS_USED] = used
        if total is not None:
            jffs[ARMemoryType.JFFS_TOTAL] = total
        if used is not None and total is not None:
            jffs[ARMemoryType.JFFS_FREE] = total - used
        return jffs

    # From 388.7: a single `free` value
    free = _mb_to_bytes(value)
    if free is not None:
        jffs[ARMemoryType.JFFS_FREE] = free
    return jffs


def _translate_memory(data: dict[str, Any]) -> dict[ARMemoryType, int]:
    """Translate memory values into bytes."""

    raw = data.get("mem_stats_arr") or ()
    memory = _map_positional(raw, _MEMORY_MB_FIELDS.items(), _mb_to_bytes)

    if len(raw) > _MEMORY_NVRAM_INDEX:
        nvram = raw_to_int(raw[_MEMORY_NVRAM_INDEX])
        if nvram is not None:
            memory[ARMemoryType.NVRAM] = nvram

    if len(raw) > _MEMORY_JFFS_INDEX:
        memory.update(_translate_jffs(raw[_MEMORY_JFFS_INDEX]))

    return memory


def _translate_load_average(data: dict[str, Any]) -> dict[int, float]:
    """Translate the 1/5/15-minute load averages."""

    raw = data.get("cpu_stats_arr") or ()
    return _map_positional(raw, enumerate(_LOAD_AVERAGE_WINDOWS), raw_to_float)


class ARSysInfoSource(ARDataSource):
    """SysInfo data source for the connected router (Merlin firmware)."""


# Universal instance - preferred
ARSysInfoSourceUniversal: ARSysInfoSource = ARSysInfoSource()


async def get_state(
    callback: ARCallbackType,
    source: ARSysInfoSource,
    **kwargs: Any,
) -> dict[str, Any]:
    """Fetch the raw sysinfo JS variables."""

    response = await callback(endpoint=AREndpoint.FETCH_SYSINFO)

    if not isinstance(response, dict):
        return {}

    return response


def translate_state(
    data: dict[str, Any],
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[ARSysInfoType, Any]:
    """Translate raw sysinfo variables into typed data categories."""

    result: dict[ARSysInfoType, Any] = {}

    wlan = _translate_wlan(data, _wlan_index_to_band(identity))
    if wlan:
        result[ARSysInfoType.WLAN] = wlan

    connections = _translate_connections(data)
    if connections:
        result[ARSysInfoType.CONNECTIONS] = connections

    memory = _translate_memory(data)
    if memory:
        result[ARSysInfoType.MEMORY] = memory

    load_average = _translate_load_average(data)
    if load_average:
        result[ARSysInfoType.LOAD_AVERAGE] = load_average

    return result


ARCallReg.register_module(
    ARSysInfoSource, get_state=get_state, translate_state=translate_state
)


__all__ = [
    "ARSysInfoSource",
    "ARSysInfoSourceUniversal",
    "get_state",
    "translate_state",
]
