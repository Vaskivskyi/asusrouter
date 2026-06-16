"""Supported platform."""

from __future__ import annotations

from asusrouter.modules.platform import ARPlatform
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_enum_translator

translate_platform = make_enum_translator(
    {
        ARSupportValue.PLATFORM_BROADCOM.value: ARPlatform.BROADCOM,
        ARSupportValue.PLATFORM_MEDIATEK.value: ARPlatform.MEDIATEK,
        ARSupportValue.PLATFORM_QUALCOMM.value: ARPlatform.QUALCOMM,
        ARSupportValue.PLATFORM_LANTIQ.value: ARPlatform.LANTIQ,
    },
    ARPlatform.UNKNOWN,
)
