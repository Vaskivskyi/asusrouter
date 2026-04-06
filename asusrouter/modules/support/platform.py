"""Supported platform."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.readers import is_true_in_dict


class ARSupportPlatform(FromStrMixin, StrEnum):
    """Platform types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    BROADCOM = "broadcom"
    LANTIQ = "lantiq"
    MEDIATEK = "mediatek"
    QUALCOMM = "qualcomm"


def translate_platform(data: dict[str, Any]) -> ARSupportPlatform:
    """Translate platform data to ARSupportPlatform."""

    if not isinstance(data, dict):
        return ARSupportPlatform.UNKNOWN  # type: ignore[unreachable]

    # Because lantic
    platform_map = {
        ARSupportValue.PLATFORM_BROADCOM: ARSupportPlatform.BROADCOM,
        ARSupportValue.PLATFORM_MEDIATEK: ARSupportPlatform.MEDIATEK,
        ARSupportValue.PLATFORM_QUALCOMM: ARSupportPlatform.QUALCOMM,
        ARSupportValue.PLATFORM_LANTIQ: ARSupportPlatform.LANTIQ,
    }

    for key, platform in platform_map.items():
        if is_true_in_dict(key.value, data):
            return platform

    return ARSupportPlatform.UNKNOWN
