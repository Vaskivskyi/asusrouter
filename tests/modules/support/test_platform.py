"""Tests for the support platform module."""

from typing import Any

import pytest

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.platform import (
    ARSupportPlatform,
    translate_platform,
)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, ARSupportPlatform.UNKNOWN),
        ({ARSupportValue.PLATFORM_BROADCOM: 1}, ARSupportPlatform.BROADCOM),
        ({ARSupportValue.PLATFORM_MEDIATEK: 1}, ARSupportPlatform.MEDIATEK),
        ({ARSupportValue.PLATFORM_QUALCOMM: 1}, ARSupportPlatform.QUALCOMM),
        ({ARSupportValue.PLATFORM_LANTIQ: 1}, ARSupportPlatform.LANTIQ),
        # Multiple true, should return the first found
        (
            {
                ARSupportValue.PLATFORM_BROADCOM: 1,
                ARSupportValue.PLATFORM_LANTIQ: 1,
            },
            ARSupportPlatform.BROADCOM,
        ),
        # All false
        (
            {
                ARSupportValue.PLATFORM_BROADCOM: 0,
                ARSupportValue.PLATFORM_LANTIQ: 0,
            },
            ARSupportPlatform.UNKNOWN,
        ),
        # String values
        (
            {ARSupportValue.PLATFORM_BROADCOM: "enabled"},
            ARSupportPlatform.BROADCOM,
        ),
        ({ARSupportValue.PLATFORM_LANTIQ: "on"}, ARSupportPlatform.LANTIQ),
        (
            {
                ARSupportValue.PLATFORM_BROADCOM: "0",
                ARSupportValue.PLATFORM_QUALCOMM: "1",
            },
            ARSupportPlatform.QUALCOMM,
        ),
        # Not a dict
        ("not_a_dict", ARSupportPlatform.UNKNOWN),
    ],
)
def test_translate_platform(
    data: dict[str, Any], expected: ARSupportPlatform
) -> None:
    """Test translate_platform returns correct platform type."""

    result = translate_platform(data)
    assert result == expected
