"""Tests for the support Aura module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.aura import ARAuraCapability
from asusrouter.modules.support.aura import (
    translate_aura,
    translate_aura_capabilities,
)
from asusrouter.modules.support.flag import ARSupportValue


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.AURA.value: 1}, True),
        ({ARSupportValue.AURA.value: "0"}, False),
        ({}, False),
    ],
)
def test_translate_aura(data: Any, expected: bool) -> None:
    """Test translate_aura returns correct aura support flag."""

    assert translate_aura(data) is expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, {}),
        (
            {ARSupportValue.AURA_NIGHT_MODE.value: 1},
            {ARAuraCapability.NIGHT_MODE: True},
        ),
        # ZONE carries the zone count, present only when > 0
        (
            {ARSupportValue.AURA_ZONE.value: 4},
            {ARAuraCapability.ZONE: 4},
        ),
        ({ARSupportValue.AURA_ZONE.value: "0"}, {}),
        (
            {
                ARSupportValue.AURA_NIGHT_MODE.value: 1,
                ARSupportValue.AURA_ZONE.value: 3,
            },
            {
                ARAuraCapability.NIGHT_MODE: True,
                ARAuraCapability.ZONE: 3,
            },
        ),
    ],
)
def test_translate_aura_capabilities(
    data: Any, expected: dict[ARAuraCapability, bool | int]
) -> None:
    """Test translate_aura_capabilities maps Aura capabilities."""

    assert translate_aura_capabilities(data) == expected
