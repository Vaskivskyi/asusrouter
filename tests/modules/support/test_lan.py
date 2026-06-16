"""Tests for the support lan module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.lan import ARLANCapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.lan import translate_lan_capabilities


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, []),
        # Aggregation
        (
            {ARSupportValue.LAN_AGGREGATION.value: 1},
            [ARLANCapability.AGGREGATION],
        ),
        (
            {ARSupportValue.LAN_AGGREGATION.value: "1"},
            [ARLANCapability.AGGREGATION],
        ),
        # False
        ({ARSupportValue.LAN_AGGREGATION.value: 0}, []),
        # Not a dict
        ("not_a_dict", []),
        (None, []),
    ],
)
def test_translate_lan_capabilities(
    data: Any, expected: list[ARLANCapability]
) -> None:
    """Test translate_lan_capabilities returns correct capability list."""

    assert translate_lan_capabilities(data) == expected
