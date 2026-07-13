"""Firmware module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.firmware.enums import (
    AR_FW_MERLIN_LIKE,
    ARFirmwareType,
    ARFirmwareWebError,
    ARFirmwareWebFetch,
    ARFirmwareWebNotify,
    ARFirmwareWebUpgrade,
)
from asusrouter.modules.firmware.source import (
    ARFirmwareSignature,
    ARFirmwareSource,
    ARFirmwareSourceUniversal,
    ARFirmwareState,
    ARFirmwareSync,
    ARFirmwareWeb,
    get_state,
    translate_state,
)
from asusrouter.modules.firmware.version import AR_FW_388, ARFirmware

__all__ = [
    "AR_FW_388",
    "AR_FW_MERLIN_LIKE",
    "ARFirmware",
    "ARFirmwareSignature",
    "ARFirmwareSource",
    "ARFirmwareSourceUniversal",
    "ARFirmwareState",
    "ARFirmwareSync",
    "ARFirmwareType",
    "ARFirmwareWeb",
    "ARFirmwareWebError",
    "ARFirmwareWebFetch",
    "ARFirmwareWebNotify",
    "ARFirmwareWebUpgrade",
    "get_state",
    "translate_state",
]
