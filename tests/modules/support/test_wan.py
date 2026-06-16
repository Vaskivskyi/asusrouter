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
        # No nowan flag → WAN present
        ({}, True),
        ({ARSupportValue.WAN_NOWAN.value: 0}, True),
        ({"other_key": 1}, True),
        # nowan truthy → no WAN
        ({ARSupportValue.WAN_NOWAN.value: 1}, False),
        ({ARSupportValue.WAN_NOWAN.value: "1"}, False),
        # Not a dict
        ("not_a_dict", False),
        (None, False),
    ],
)
def test_translate_wan(data: Any, expected: bool) -> None:
    """Test translate_wan returns correct WAN availability."""

    assert translate_wan(data) == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, []),
        # Aggregation only
        (
            {ARSupportValue.WAN_AGGREGATION.value: 1},
            [ARWANCapability.AGGREGATION],
        ),
        (
            {ARSupportValue.WAN_AGGREGATION.value: "1"},
            [ARWANCapability.AGGREGATION],
        ),
        # DualWAN only
        (
            {ARSupportValue.WAN_DUALWAN.value: 1},
            [ARWANCapability.DUALWAN],
        ),
        (
            {ARSupportValue.WAN_DUALWAN.value: "1"},
            [ARWANCapability.DUALWAN],
        ),
        # Both
        (
            {
                ARSupportValue.WAN_AGGREGATION.value: 1,
                ARSupportValue.WAN_DUALWAN.value: 1,
            },
            [ARWANCapability.AGGREGATION, ARWANCapability.DUALWAN],
        ),
        # Both false
        (
            {
                ARSupportValue.WAN_AGGREGATION.value: 0,
                ARSupportValue.WAN_DUALWAN.value: 0,
            },
            [],
        ),
        # Not a dict
        ("not_a_dict", []),
        (None, []),
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
        # Missing key → 0
        ({}, 0),
        ({ARSupportValue.WAN_LIMIT.value: None}, 0),
        # Integer values
        ({ARSupportValue.WAN_LIMIT.value: 0}, 0),
        ({ARSupportValue.WAN_LIMIT.value: 1}, 1),
        ({ARSupportValue.WAN_LIMIT.value: 2}, 2),
        # String integers
        ({ARSupportValue.WAN_LIMIT.value: "1"}, 1),
        ({ARSupportValue.WAN_LIMIT.value: "2"}, 2),
        # Not a dict
        ("not_a_dict", 0),
        (None, 0),
    ],
)
def test_translate_wan_limit(data: Any, expected: int) -> None:
    """Test translate_wan_limit returns correct WAN limit."""

    assert translate_wan_limit(data) == expected
