"""Firmware module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.firmware.legacy import (
    Firmware,
    FirmwareType,
    WebsError,
    WebsFlag,
    WebsUpdate,
    WebsUpgrade,
)

__all__ = [
    "Firmware",
    "FirmwareType",
    "WebsError",
    "WebsFlag",
    "WebsUpdate",
    "WebsUpgrade",
]
