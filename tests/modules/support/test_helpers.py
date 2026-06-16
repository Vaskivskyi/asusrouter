"""Tests for the support helpers module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.support.helpers import (
    make_bool_translator,
    make_int_translator,
)


@pytest.mark.parametrize(
    ("key", "negate", "data", "expected"),
    [
        # negate=False: absent or false → False
        ("k", False, {}, False),
        ("k", False, {"k": 0}, False),
        ("k", False, {"k": "0"}, False),
        ("k", False, {"other": 1}, False),
        # negate=False: key true → True
        ("k", False, {"k": 1}, True),
        ("k", False, {"k": "1"}, True),
        # negate=False: non-dict → False
        ("k", False, "not_a_dict", False),
        ("k", False, None, False),
        # negate=True: key absent or false → True
        ("k", True, {}, True),
        ("k", True, {"k": 0}, True),
        # negate=True: key true → False
        ("k", True, {"k": 1}, False),
        ("k", True, {"k": "1"}, False),
        # negate=True: non-dict → False
        ("k", True, "not_a_dict", False),
        ("k", True, None, False),
    ],
)
def test_make_bool_translator(
    key: str, negate: bool, data: Any, expected: bool
) -> None:
    """Test make_bool_translator returns a correct bool translator."""

    translator = make_bool_translator(key, negate=negate)
    assert translator(data) is expected


@pytest.mark.parametrize(
    ("key", "data", "expected"),
    [
        # absent → 0
        ("k", {}, 0),
        # zero values → 0
        ("k", {"k": 0}, 0),
        ("k", {"k": "0"}, 0),
        # positive values
        ("k", {"k": 1}, 1),
        ("k", {"k": 2}, 2),
        ("k", {"k": "1"}, 1),
        # invalid string → 0
        ("k", {"k": "invalid"}, 0),
        # wrong key → 0
        ("k", {"other": 1}, 0),
        # non-dict → 0
        ("k", "not_a_dict", 0),
        ("k", None, 0),
    ],
)
def test_make_int_translator(key: str, data: Any, expected: int) -> None:
    """Test make_int_translator returns a correct int translator."""

    translator = make_int_translator(key)
    assert translator(data) == expected
