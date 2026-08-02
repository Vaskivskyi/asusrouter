"""Supported firmware features."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.firmware.enums import ARFirmwareCapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.tools.readers import is_true_in_dict

_CAPABILITY_FLAGS = {
    ARSupportValue.FIRMWARE_AUTO_UPGRADE.value: (
        ARFirmwareCapability.AUTO_UPGRADE
    ),
    ARSupportValue.FIRMWARE_BETA.value: ARFirmwareCapability.BETA,
    ARSupportValue.FIRMWARE_REVERT.value: ARFirmwareCapability.REVERT,
}


def translate_firmware_capabilities(
    data: dict[str, Any],
) -> dict[ARFirmwareCapability, bool]:
    """Map advertised firmware-management capabilities."""

    capabilities: dict[ARFirmwareCapability, bool] = {
        capability: True
        for key, capability in _CAPABILITY_FLAGS.items()
        if is_true_in_dict(key, data)
    }

    if is_true_in_dict(
        ARSupportValue.FIRMWARE_LIVE_UPDATE.value, data
    ) and not is_true_in_dict(ARSupportValue.FIRMWARE_NO_UPDATE.value, data):
        capabilities[ARFirmwareCapability.LIVE_UPDATE] = True

    # Manual upload is available unless the device opts out
    if not is_true_in_dict(ARSupportValue.FIRMWARE_NO_MANUAL.value, data):
        capabilities[ARFirmwareCapability.MANUAL_UPLOAD] = True
    return capabilities


def translate_firmware(data: dict[str, Any]) -> bool:
    """Report whether the device advertises any firmware capability."""

    return bool(translate_firmware_capabilities(data))
