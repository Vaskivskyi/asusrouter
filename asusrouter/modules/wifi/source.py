"""WiFi data source for AsusRouter."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.endpoint_v2.hooks import ARHook, hook_request
from asusrouter.modules.nvram import ARNvramIndexSource, ARNvramIndexType
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.wifi.enums import (
    ARWiFiBand,
    ARWiFiBandwidth,
    ARWiFiField,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters_v2.raw import (
    raw_convert,
    raw_to_bool,
    raw_to_int,
    raw_to_str,
)
from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.readers_v2.table import read_table
from asusrouter.tools.types import ARCallbackType

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity


# Raw `bw` index -> bandwidth (Broadcom); index 4 is unused
_BW_INDEX: dict[int, ARWiFiBandwidth] = {
    0: ARWiFiBandwidth.AUTO,
    1: ARWiFiBandwidth.WIDTH_20,
    2: ARWiFiBandwidth.WIDTH_40,
    3: ARWiFiBandwidth.WIDTH_80,
    5: ARWiFiBandwidth.WIDTH_160,
    6: ARWiFiBandwidth.WIDTH_320,
}


def _read_bandwidth(value: Any) -> ARWiFiBandwidth | None:
    """Map the raw `bw` index to a bandwidth, or None if unknown."""

    index = raw_to_int(value)
    return _BW_INDEX.get(index) if index is not None else None


# A key template/hook, the field it maps to, and its converter
_FieldMap = tuple[ARNvramIndexType, ARWiFiField, Callable[[Any], Any]]
_HookMap = tuple[ARHook, ARWiFiField, Callable[[Any], Any]]

# Per-radio hooks whose response is a list indexed by wireless unit
_HOOK_UNIT_ARRAYS: tuple[_HookMap, ...] = (
    (ARHook.WL_CONTROL_CHANNEL, ARWiFiField.CHANNEL, raw_to_int),
)

# nvram keys stored per band, prefixed with the band value (e.g. `2g1_bw`)
_BAND_KEYS: tuple[_FieldMap, ...] = (
    (ARNvramIndexType.WL_BAND_NMODE, ARWiFiField.WIRELESS_MODE, raw_to_int),
    (ARNvramIndexType.WL_BAND_BW, ARWiFiField.BANDWIDTH, _read_bandwidth),
    (ARNvramIndexType.WL_BAND_CHANSPEC, ARWiFiField.CHANNEL_SPEC, raw_to_str),
    (ARNvramIndexType.WL_BAND_NCTRLSB, ARWiFiField.SIDE_BAND, raw_to_str),
    (ARNvramIndexType.WL_BAND_BW_160, ARWiFiField.ENABLE_160MHZ, raw_to_bool),
    (ARNvramIndexType.WL_BAND_BW_240, ARWiFiField.ENABLE_240MHZ, raw_to_bool),
    (ARNvramIndexType.WL_BAND_11BE, ARWiFiField.WIFI7, raw_to_bool),
)

# nvram keys stored per unit, prefixed with the interface (e.g. `wl0_hwaddr`)
_UNIT_KEYS: tuple[_FieldMap, ...] = (
    (ARNvramIndexType.WL_RADIO, ARWiFiField.STATE, raw_to_bool),
    (ARNvramIndexType.WL_COUNTRY_CODE, ARWiFiField.COUNTRY, raw_to_str),
    (ARNvramIndexType.WL_VERSION, ARWiFiField.DRIVER, raw_to_str),
    (ARNvramIndexType.WL_HWADDR, ARWiFiField.MAC, MacAddress.from_value_safe),
)

# appGet hooks that yield the per-unit radio arrays
_WIFI_HOOKS = tuple(hook for hook, _, _ in _HOOK_UNIT_ARRAYS)


class ARWiFiSource(ARDataSource):
    """AsusRouter WiFi data source (router-global, all bands)."""


# Universal instance - preferred
ARWiFiSourceUniversal: ARWiFiSource = ARWiFiSource()


def _build_request(identity: ARDeviceIdentity | None) -> str | None:
    """Build the appGet request for all WiFi bands of the device."""

    wifi = identity.wifi if identity is not None else None
    if not wifi:
        return None

    items: list[ARNvramIndexSource] = []
    for band, unit in wifi.items():
        items.extend(
            ARNvramIndexSource(kind, band.value) for kind, _, _ in _BAND_KEYS
        )
        items.extend(
            ARNvramIndexSource(kind, unit) for kind, _, _ in _UNIT_KEYS
        )

    return hook_request(*_WIFI_HOOKS, *items)


async def get_state(
    callback: ARCallbackType,
    source: ARWiFiSource,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> Any:
    """Fetch the raw WiFi hooks and nvram config for all bands."""

    request = _build_request(identity)
    if request is None:
        return {}

    return await callback(endpoint=AREndpoint.FETCH_DATA, request=request)


def _array_at(value: Any, index: int) -> Any:
    """Return the item at `index` of a list, or None."""

    if isinstance(value, list) and 0 <= index < len(value):
        return value[index]
    return None


def _translate_band(
    data: dict[str, Any], band: ARWiFiBand, unit: int
) -> dict[ARWiFiField, Any]:
    """Build the field dict for a single band/unit."""

    fields: dict[ARWiFiField, Any] = {}

    for hook, field, converter in _HOOK_UNIT_ARRAYS:
        value = raw_convert(_array_at(data.get(hook.value), unit), converter)
        if value is not None:
            fields[field] = value

    fields.update(
        read_table(data, _BAND_KEYS, key=lambda kind: kind.key(band.value))
    )
    fields.update(
        read_table(data, _UNIT_KEYS, key=lambda kind: kind.key(unit))
    )

    return fields


def translate_state(
    data: Any,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[ARWiFiBand, dict[ARWiFiField, Any]]:
    """Translate raw WiFi data into the per-band field dict."""

    if not isinstance(data, dict) or identity is None or not identity.wifi:
        return {}

    result: dict[ARWiFiBand, dict[ARWiFiField, Any]] = {}
    for band, unit in identity.wifi.items():
        fields = _translate_band(data, band, unit)
        if fields:
            result[band] = fields

    return result


ARCallReg.register_module(
    ARWiFiSource, get_state=get_state, translate_state=translate_state
)


__all__ = [
    "ARWiFiSource",
    "ARWiFiSourceUniversal",
    "get_state",
    "translate_state",
]
