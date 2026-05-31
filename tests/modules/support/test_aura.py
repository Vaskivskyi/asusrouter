"""Tests for the support Aura module."""

from typing import Any

import pytest

from asusrouter.modules.support.aura import (
    translate_aura,
    translate_aura_night_mode,
    translate_aura_zone,
)
from asusrouter.modules.support.flag import ARSupportValue


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, False),
        ({ARSupportValue.AURA.value: 1}, True),
        ({ARSupportValue.AURA.value: "enabled"}, True),
        ({ARSupportValue.AURA.value: 0}, False),
        ("not_a_dict", False),
    ],
)
def test_translate_aura(data: Any, expected: bool) -> None:
    """Test translate_aura returns correct aura support flag."""

    assert translate_aura(data) is expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, False),
        ({ARSupportValue.AURA_NIGHT_MODE.value: 1}, True),
        ({ARSupportValue.AURA_NIGHT_MODE.value: "enabled"}, True),
        ({ARSupportValue.AURA_NIGHT_MODE.value: 0}, False),
        ("not_a_dict", False),
    ],
)
def test_translate_aura_night_mode(data: Any, expected: bool) -> None:
    """Test translate_aura_night_mode returns correct night mode flag."""

    assert translate_aura_night_mode(data) is expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, 0),
        ({ARSupportValue.AURA_ZONE.value: 1}, 1),
        ({ARSupportValue.AURA_ZONE.value: "2"}, 2),
        ({ARSupportValue.AURA_ZONE.value: "invalid"}, 0),
        ("not_a_dict", 0),
    ],
)
def test_translate_aura_zone(data: Any, expected: int) -> None:
    """Test translate_aura_zone returns correct zone count."""

    assert translate_aura_zone(data) == expected
