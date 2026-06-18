"""Device module for AsusRouter.

This module describes the physical device and identity.
It's a single-point source for all device information and features.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any

from asusrouter.const import (
    AR_CALL_GET_STATE,
    AR_CALL_TRANSLATE_STATE,
    UNKNOWN_MEMBER,
)
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.source import ARDataSource, ARDataType
from asusrouter.modules.support import ARSupportSourceUniversal
from asusrouter.registry import (
    ARCallableEntry,
    ARCallableRegistry as ARCallReg,
)
from asusrouter.tools.enum import FromIntMixin
from asusrouter.tools.types import ARCallbackType


class ARDeviceSource(ARDataSource):
    """AsusRouter device.

    A source representation of the physical device and its identity.
    """


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


calls: dict[str, ARCallableEntry] = {
    AR_CALL_GET_STATE: get_state,
    AR_CALL_TRANSLATE_STATE: translate_state,
}

ARCallReg.register(ARDeviceSource, **calls)


# TODO: Redo this legacy class
class DeviceOperationMode(FromIntMixin, IntEnum):
    """Types of device operation modes.

    Known modes
    ---
    - **ROUTER**
    - **REPEATER**
    - **ACCESS_POINT**
    - **MEDIA_BRIDGE**
    - **AIMESH_NODE**
    """

    UNKNOWN = UNKNOWN_MEMBER

    ROUTER = 1
    REPEATER = 2
    ACCESS_POINT = 3
    MEDIA_BRIDGE = 4
    AIMESH_NODE = 5
