"""Tests for the support helpers module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.support.helpers import (
    make_bool_translator,
    make_enum_translator,
    make_int_translator,
    make_list_translator,
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


@pytest.mark.parametrize(
    ("table", "data", "expected"),
    [
        # empty dict → empty list
        ({"k1": "v1"}, {}, []),
        # key present → item in list
        ({"k1": "v1"}, {"k1": 1}, ["v1"]),
        ({"k1": "v1"}, {"k1": "1"}, ["v1"]),
        # key false → empty
        ({"k1": "v1"}, {"k1": 0}, []),
        ({"k1": "v1"}, {"k1": "0"}, []),
        # wrong key → empty
        ({"k1": "v1"}, {"k2": 1}, []),
        # multiple keys — all true
        ({"k1": "v1", "k2": "v2"}, {"k1": 1, "k2": 1}, ["v1", "v2"]),
        # multiple keys — partial
        ({"k1": "v1", "k2": "v2"}, {"k1": 1}, ["v1"]),
        ({"k1": "v1", "k2": "v2"}, {"k2": 1}, ["v2"]),
        # non-dict → empty
        ({"k1": "v1"}, "not_a_dict", []),
        ({"k1": "v1"}, None, []),
    ],
)
def test_make_list_translator(
    table: dict[str, str], data: Any, expected: list[str]
) -> None:
    """Test make_list_translator returns a correct list translator."""

    translator = make_list_translator(table)
    assert translator(data) == expected


@pytest.mark.parametrize(
    ("table", "default", "data", "expected"),
    [
        # no match → default
        ({"k1": "v1"}, "d", {}, "d"),
        ({"k1": "v1"}, "d", {"k1": 0}, "d"),
        ({"k1": "v1"}, "d", {"k1": "0"}, "d"),
        ({"k1": "v1"}, "d", {"k2": 1}, "d"),
        # single key match
        ({"k1": "v1"}, "d", {"k1": 1}, "v1"),
        ({"k1": "v1"}, "d", {"k1": "1"}, "v1"),
        # first key wins
        ({"k1": "v1", "k2": "v2"}, "d", {"k1": 1, "k2": 1}, "v1"),
        # second key when first absent
        ({"k1": "v1", "k2": "v2"}, "d", {"k2": 1}, "v2"),
        # non-dict → default
        ({"k1": "v1"}, "d", "not_a_dict", "d"),
        ({"k1": "v1"}, "d", None, "d"),
    ],
)
def test_make_enum_translator(
    table: dict[str, str], default: str, data: Any, expected: str
) -> None:
    """Test make_enum_translator returns first match or default."""

    translator = make_enum_translator(table, default)
    assert translator(data) == expected
