"""Tests for the support wan module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.wan import (
    translate_wan,
    translate_wan_capabilities,
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
        ({}, {}),
        (
            {ARSupportValue.WAN_AGGREGATION.value: 1},
            {ARWANCapability.AGGREGATION: True},
        ),
        (
            {ARSupportValue.WAN_DUALWAN.value: 1},
            {ARWANCapability.DUALWAN: True},
        ),
        # LIMIT carries the port count, present only when reported
        (
            {ARSupportValue.WAN_LIMIT.value: 2},
            {ARWANCapability.LIMIT: 2},
        ),
        ({ARSupportValue.WAN_LIMIT.value: "0"}, {}),
        (
            {
                ARSupportValue.WAN_AGGREGATION.value: 1,
                ARSupportValue.WAN_DUALWAN.value: 1,
                ARSupportValue.WAN_LIMIT.value: 2,
            },
            {
                ARWANCapability.AGGREGATION: True,
                ARWANCapability.DUALWAN: True,
                ARWANCapability.LIMIT: 2,
            },
        ),
    ],
)
def test_translate_wan_capabilities(
    data: Any, expected: dict[ARWANCapability, bool | int]
) -> None:
    """Test translate_wan_capabilities maps WAN capabilities."""

    assert translate_wan_capabilities(data) == expected
