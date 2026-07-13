"""Device data source for AsusRouter."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.nvram import (
    ARNvramIndexSource,
    ARNvramIndexType,
    ARNvramType,
)
from asusrouter.modules.source import ARDataSource, ARDataType
from asusrouter.modules.support import ARSupportSourceUniversal
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.types import ARCallbackType


class ARDeviceSource(ARDataSource):
    """AsusRouter device."""


# A universal instance of the device source (preferred)
ARDeviceSourceUniversal: ARDeviceSource = ARDeviceSource()


DEVICE_REQUEST: tuple[ARDataType | ARDataSource, ...] = (
    # Device information
    ARNvramType.MAC,
    ARNvramType.MODEL,
    ARNvramType.MODEL_ORIGINAL,
    ARNvramType.SECRET_CODE,
    ARNvramType.SERIAL,
    ARNvramType.WIRELESS_BANDS,
    # Per-radio band type, for the wifi fallback when WIRELESS_BANDS is empty
    *(ARNvramIndexSource(ARNvramIndexType.WL_NBAND, i) for i in range(4)),
    # Firmware information
    ARNvramType.FW_MAJOR,
    ARNvramType.FW_MINOR,
    ARNvramType.FW_BUILD,
    ARNvramType.FW_SWPJ,
    # Software information
    ARNvramType.SW_MODE,
    ARSupportSourceUniversal,
)


async def get_state(
    callback: ARCallbackType,
    source: ARDeviceSource,
    get_data_callback: ARCallbackType,
    **kwargs: Any,
) -> Any:
    """Fetch the device state.

    This is a special case where we need to fetch data from other sources.
    """

    return await get_data_callback(DEVICE_REQUEST)


def translate_state(
    data: dict[str, Any],
    **kwargs: Any,
) -> ARDeviceIdentity:
    """Translate the device state."""

    return ARDeviceIdentity.build(data)


ARCallReg.register_module(
    ARDeviceSource, get_state=get_state, translate_state=translate_state
)


__all__ = [
    "ARDeviceSource",
    "ARDeviceSourceUniversal",
    "DEVICE_REQUEST",
    "get_state",
    "translate_state",
]
