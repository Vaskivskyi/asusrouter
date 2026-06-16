"""Tests for the support speedtest module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.speedtest import ARSpeedTestCapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.speedtest import (
    translate_speedtest,
    translate_speedtest_capabilities,
)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.SPEEDTEST.value: 1}, True),
        ({ARSupportValue.SPEEDTEST.value: "0"}, False),
        ({}, False),
    ],
)
def test_translate_speedtest(data: Any, expected: bool) -> None:
    """Test translate_speedtest returns correct SpeedTest support value."""

    assert translate_speedtest(data) is expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, []),
        # 10G
        (
            {ARSupportValue.SPEEDTEST_10G.value: 1},
            [ARSpeedTestCapability.SPEED_10G],
        ),
        (
            {ARSupportValue.SPEEDTEST_10G.value: "1"},
            [ARSpeedTestCapability.SPEED_10G],
        ),
        # False
        ({ARSupportValue.SPEEDTEST_10G.value: 0}, []),
        # Not a dict
        ("not_a_dict", []),
        (None, []),
    ],
)
def test_translate_speedtest_capabilities(
    data: Any, expected: list[ARSpeedTestCapability]
) -> None:
    """Test translate_speedtest_capabilities returns correct capabilities."""

    assert translate_speedtest_capabilities(data) == expected
