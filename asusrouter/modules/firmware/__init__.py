"""Firmware module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.firmware.enums import (
    AR_FW_MERLIN_LIKE,
    ARFirmwareCapability,
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
    fetch_state,
    translate_state,
)
from asusrouter.modules.firmware.version import AR_FW_388, ARFirmware

__all__ = [
    "AR_FW_388",
    "AR_FW_MERLIN_LIKE",
    "ARFirmware",
    "ARFirmwareCapability",
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
    "fetch_state",
    "translate_state",
]
