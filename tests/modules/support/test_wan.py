"""Tests for the support wan module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.wan import (
    translate_wan,
    translate_wan_capabilities,
    translate_wan_limit,
)
from asusrouter.modules.wan import ARWANCapability


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.WAN_NOWAN.value: 1}, False),
        ({ARSupportValue.WAN_NOWAN.value: "0"}, True),
        ({}, True),
    ],
)
def test_translate_wan(data: Any, expected: bool) -> None:
    """Test translate_wan returns correct WAN availability."""

    assert translate_wan(data) is expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (
            {ARSupportValue.WAN_AGGREGATION.value: 1},
            [ARWANCapability.AGGREGATION],
        ),
        ({ARSupportValue.WAN_DUALWAN.value: 1}, [ARWANCapability.DUALWAN]),
        ({}, []),
    ],
)
def test_translate_wan_capabilities(
    data: Any, expected: list[ARWANCapability]
) -> None:
    """Test translate_wan_capabilities returns correct capability list."""

    assert translate_wan_capabilities(data) == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.WAN_LIMIT.value: 2}, 2),
        ({ARSupportValue.WAN_LIMIT.value: "0"}, 0),
        ({}, 0),
    ],
)
def test_translate_wan_limit(data: Any, expected: int) -> None:
    """Test translate_wan_limit returns correct WAN limit."""

    assert translate_wan_limit(data) == expected
