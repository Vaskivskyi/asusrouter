"""Device module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.device.enums import DeviceOperationMode
from asusrouter.modules.device.source import (
    DEVICE_REQUEST,
    ARDeviceSource,
    ARDeviceSourceUniversal,
    get_state,
    translate_state,
)

__all__ = [
    "ARDeviceSource",
    "ARDeviceSourceUniversal",
    "DEVICE_REQUEST",
    "DeviceOperationMode",
    "get_state",
    "translate_state",
]
