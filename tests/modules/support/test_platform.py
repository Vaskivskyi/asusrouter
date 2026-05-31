"""Tests for the support platform module."""

from typing import Any

import pytest

from asusrouter.modules.platform import ARPlatform
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.platform import translate_platform


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, ARPlatform.UNKNOWN),
        ({ARSupportValue.PLATFORM_BROADCOM: 1}, ARPlatform.BROADCOM),
        ({ARSupportValue.PLATFORM_MEDIATEK: 1}, ARPlatform.MEDIATEK),
        ({ARSupportValue.PLATFORM_QUALCOMM: 1}, ARPlatform.QUALCOMM),
        ({ARSupportValue.PLATFORM_LANTIQ: 1}, ARPlatform.LANTIQ),
        # Multiple true, should return the first found
        (
            {
                ARSupportValue.PLATFORM_BROADCOM: 1,
                ARSupportValue.PLATFORM_LANTIQ: 1,
            },
            ARPlatform.BROADCOM,
        ),
        # All false
        (
            {
                ARSupportValue.PLATFORM_BROADCOM: 0,
                ARSupportValue.PLATFORM_LANTIQ: 0,
            },
            ARPlatform.UNKNOWN,
        ),
        # String values
        (
            {ARSupportValue.PLATFORM_BROADCOM: "enabled"},
            ARPlatform.BROADCOM,
        ),
        ({ARSupportValue.PLATFORM_LANTIQ: "on"}, ARPlatform.LANTIQ),
        (
            {
                ARSupportValue.PLATFORM_BROADCOM: "0",
                ARSupportValue.PLATFORM_QUALCOMM: "1",
            },
            ARPlatform.QUALCOMM,
        ),
        # Not a dict
        ("not_a_dict", ARPlatform.UNKNOWN),
    ],
)
def test_translate_platform(
    data: dict[str, Any], expected: ARPlatform
) -> None:
    """Test translate_platform returns correct platform type."""

    result = translate_platform(data)
    assert result == expected
