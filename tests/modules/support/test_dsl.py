"""Tests for the support dsl module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.support.dsl import translate_dsl
from asusrouter.modules.support.flag import ARSupportValue


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        # No DSL flag → no DSL
        ({}, False),
        ({ARSupportValue.DSL.value: 0}, False),
        ({"other_key": 1}, False),
        # DSL flag truthy → DSL present
        ({ARSupportValue.DSL.value: 1}, True),
        ({ARSupportValue.DSL.value: "1"}, True),
        # Not a dict
        ("not_a_dict", False),
        (None, False),
    ],
)
def test_translate_dsl(data: Any, expected: bool) -> None:
    """Test translate_dsl returns correct DSL support value."""

    assert translate_dsl(data) == expected
