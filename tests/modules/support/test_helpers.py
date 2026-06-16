"""Tests for the support helpers module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.support.helpers import make_bool_translator


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
