"""Supported platform."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.platform import ARPlatform
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.tools.readers import is_true_in_dict


def translate_platform(data: dict[str, Any]) -> ARPlatform:
    """Translate platform data to ARPlatform."""

    if not isinstance(data, dict):
        return ARPlatform.UNKNOWN  # type: ignore[unreachable]

    # Because lantic
    platform_map = {
        ARSupportValue.PLATFORM_BROADCOM: ARPlatform.BROADCOM,
        ARSupportValue.PLATFORM_MEDIATEK: ARPlatform.MEDIATEK,
        ARSupportValue.PLATFORM_QUALCOMM: ARPlatform.QUALCOMM,
        ARSupportValue.PLATFORM_LANTIQ: ARPlatform.LANTIQ,
    }

    for key, platform in platform_map.items():
        if is_true_in_dict(key.value, data):
            return platform

    return ARPlatform.UNKNOWN
