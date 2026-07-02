"""Temperature module for AsusRouter."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from asusrouter.config import ARConfig, ARConfigKey as ARConfKey
from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.temperature.scale import (
    scale_temperature,
    warn_temperature_scaled,
)
from asusrouter.modules.wifi import AR_WIFI_UNIT_FALLBACK, ARWiFiBand
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters_v2.raw import raw_to_float
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.types import ARCallbackType

# The temperature data can be presented in the following JS variables:
# 1) curr_coreTmp_2_raw, curr_coreTmp_5_raw, curr_coreTmp_52_raw
# 2) curr_coreTmp_0_raw, curr_coreTmp_1_raw, curr_coreTmp_2_raw,
#    curr_coreTmp_3_raw
# 3) curr_coreTmp_wl0_raw, curr_coreTmp_wl1_raw, curr_coreTmp_wl2_raw,
#    curr_coreTmp_wl3_raw
# for 2ghz, 5ghz, 5ghz2, 6ghz respectively.
# CPU temperature is set either in curr_cpuTemp or curr_coreTmp_cpu.


class ARTemperatureType(FromStrMixin, StrEnum):
    """AsusRouter temperature data type."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    CPU = "cpu"
    RADIO_2G1 = "radio_2g1"
    RADIO_2G2 = "radio_2g2"
    RADIO_5G1 = "radio_5g1"
    RADIO_5G2 = "radio_5g2"
    RADIO_6G1 = "radio_6g1"
    RADIO_6G2 = "radio_6g2"


# Static raw JS variable -> temperature type maps, one per reporting
# format. The first format whose marker key is present in the data wins.
_FORMAT_CORE_52: dict[str, ARTemperatureType] = {
    "curr_coreTmp_2_raw": ARTemperatureType.RADIO_2G1,
    "curr_coreTmp_5_raw": ARTemperatureType.RADIO_5G1,
    "curr_coreTmp_52_raw": ARTemperatureType.RADIO_5G2,
}
_FORMAT_CORE_INDEX: dict[str, ARTemperatureType] = {
    "curr_coreTmp_0_raw": ARTemperatureType.RADIO_2G1,
    "curr_coreTmp_1_raw": ARTemperatureType.RADIO_5G1,
    "curr_coreTmp_2_raw": ARTemperatureType.RADIO_5G2,
    "curr_coreTmp_3_raw": ARTemperatureType.RADIO_6G1,
}

# WiFi band -> temperature type. Used to map the wlX format dynamically
# from the device identity, where each `wl{N}` index is the band id
# reported in `identity.wifi`.
_WIFI_BAND_TO_TEMP: dict[ARWiFiBand, ARTemperatureType] = {
    ARWiFiBand.BAND_2G1: ARTemperatureType.RADIO_2G1,
    ARWiFiBand.BAND_2G2: ARTemperatureType.RADIO_2G2,
    ARWiFiBand.BAND_5G1: ARTemperatureType.RADIO_5G1,
    ARWiFiBand.BAND_5G2: ARTemperatureType.RADIO_5G2,
    ARWiFiBand.BAND_6G1: ARTemperatureType.RADIO_6G1,
    ARWiFiBand.BAND_6G2: ARTemperatureType.RADIO_6G2,
}

# Fallback for the wlX format when the device WiFi bands are unknown.
_FORMAT_WL_STATIC: dict[str, ARTemperatureType] = {
    f"curr_coreTmp_wl{unit}_raw": _WIFI_BAND_TO_TEMP[band]
    for unit, band in AR_WIFI_UNIT_FALLBACK.items()
}

# CPU temperature JS variables in priority order.
_CPU_KEYS: tuple[str, ...] = ("curr_coreTmp_cpu", "curr_cpuTemp")


def _wl_mapping(identity: ARDeviceIdentity) -> dict[str, ARTemperatureType]:
    """Build the wlX -> temperature type map from the device WiFi bands."""

    return {
        f"curr_coreTmp_wl{band_id}_raw": _WIFI_BAND_TO_TEMP[band]
        for band, band_id in identity.wifi.items()
        if band in _WIFI_BAND_TO_TEMP
    }


def _band_mapping(
    data: dict[str, Any], identity: ARDeviceIdentity
) -> dict[str, ARTemperatureType]:
    """Select the raw variable -> temperature type map for the data.

    The wlX format is resolved from `identity.wifi` when available, since
    the `wl{N}` indices are device-specific band ids; otherwise it falls
    back to a static map. The other formats are always static.
    """

    if "curr_coreTmp_5_raw" in data:
        return _FORMAT_CORE_52
    if "curr_coreTmp_0_raw" in data:
        return _FORMAT_CORE_INDEX
    if "curr_coreTmp_wl0_raw" in data:
        if identity.wifi:
            return _wl_mapping(identity)
        return _FORMAT_WL_STATIC
    return {}


class ARTemperatureSource(ARDataSource):
    """AsusRouter temperature data source."""


# Universal instance - preferred
ARTemperatureSourceUniversal: ARTemperatureSource = ARTemperatureSource()


async def get_state(
    callback: ARCallbackType,
    source: ARTemperatureSource,
    *,
    identity: ARDeviceIdentity,
    **kwargs: Any,
) -> dict[str, Any]:
    """Fetch the raw temperature JS variables."""

    response = await callback(endpoint=AREndpoint.FETCH_TEMPERATURE)

    if not isinstance(response, dict):
        return {}

    return response


def translate_state(
    data: dict[str, Any],
    *,
    identity: ARDeviceIdentity,
    **kwargs: Any,
) -> dict[ARTemperatureType, Any]:
    """Translate raw JS temperature variables to temperature values."""

    config = kwargs.get("config", ARConfig)

    raw: dict[ARTemperatureType, Any] = {}

    # Band detection — the wlX format is mapped from the device identity
    for js_var, temp_type in _band_mapping(data, identity).items():
        raw[temp_type] = data.get(js_var)

    # CPU temperature — first available source wins
    for js_var in _CPU_KEYS:
        if js_var in data:
            raw[ARTemperatureType.CPU] = data.get(js_var)
            break

    # Strip degree suffix, filter out disabled sensors, and convert to float
    temperature: dict[ARTemperatureType, Any] = {
        temp_type: raw_to_float(value.replace("&deg;C", ""))
        for temp_type, value in raw.items()
        if isinstance(value, str) and value and "disabled" not in value
    }

    if config.get(ARConfKey.OPTIMISTIC_TEMPERATURE):
        temperature, scaled = scale_temperature(temperature)
        if scaled:
            warn_temperature_scaled(config, data)

    return temperature


ARCallReg.register_module(
    ARTemperatureSource, get_state=get_state, translate_state=translate_state
)
