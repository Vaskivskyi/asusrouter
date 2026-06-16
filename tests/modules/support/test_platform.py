"""Tests for the support platform module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.platform import ARPlatform
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.platform import translate_platform


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.PLATFORM_BROADCOM.value: 1}, ARPlatform.BROADCOM),
        ({ARSupportValue.PLATFORM_MEDIATEK.value: 1}, ARPlatform.MEDIATEK),
        ({ARSupportValue.PLATFORM_QUALCOMM.value: 1}, ARPlatform.QUALCOMM),
        ({ARSupportValue.PLATFORM_LANTIQ.value: 1}, ARPlatform.LANTIQ),
        # First match wins
        (
            {
                ARSupportValue.PLATFORM_BROADCOM.value: 1,
                ARSupportValue.PLATFORM_LANTIQ.value: 1,
            },
            ARPlatform.BROADCOM,
        ),
        ({}, ARPlatform.UNKNOWN),
    ],
)
def test_translate_platform(
    data: dict[str, Any], expected: ARPlatform
) -> None:
    """Test translate_platform returns correct platform type."""

    assert translate_platform(data) == expected
