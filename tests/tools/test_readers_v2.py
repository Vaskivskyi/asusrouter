"""Tests for the readers V2 tools."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.tools.readers_v2 import read_js_section


@pytest.mark.parametrize(
    ("data", "key", "expected"),
    [
        ({"a": [{"x": 1}]}, "a", {"x": 1}),
        ({"a": [[1, 2]]}, "a", [1, 2]),
        ({"a": []}, "a", None),
        ({"a": "x"}, "a", None),
        ({}, "a", None),
        ("not-a-dict", "a", None),
    ],
    ids=["dict", "list", "empty", "not_list", "absent", "not_dict"],
)
def test_read_js_section(data: Any, key: str, expected: Any) -> None:
    """The first element of a list-cover section is returned, else None."""

    assert read_js_section(data, key) == expected
