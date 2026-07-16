"""Tests for asusrouter.tools.converters.raw."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from asusrouter.tools.converters.raw import (
    _BOM,
    _STR_TO_BOOL,
    raw_convert,
    raw_to_bool,
    raw_to_datetime,
    raw_to_float,
    raw_to_int,
    raw_to_str,
    raw_to_str_list,
)


class TestRawConvert:
    """Tests for raw_convert."""

    def test_none_and_empty(self) -> None:
        """None and empty strings are treated as no value."""

        assert raw_convert(None, str) is None
        assert raw_convert("", str) is None

    def test_value(self) -> None:
        """A value is passed through the converter."""

        assert raw_convert("5", int) == 5

    def test_empty_list_result(self) -> None:
        """An empty-list result is treated as no value."""

        assert raw_convert("x", lambda _: []) is None

    def test_zero_kept(self) -> None:
        """A zero result is kept (not treated as absent)."""

        assert raw_convert("0", int) == 0


def test_str_to_bool_type() -> None:
    """_STR_TO_BOOL is a dict mapping strings to bools."""

    assert isinstance(_STR_TO_BOOL, dict)
    assert all(isinstance(k, str) for k in _STR_TO_BOOL)
    assert all(isinstance(v, bool) for v in _STR_TO_BOOL.values())


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # Non-convertible -> None
        (None, None),
        ([], None),
        ({}, None),
        ("unknown_string", None),
        ("", None),
        # bool passthrough (checked before int/float)
        (True, True),
        (False, False),
        # int
        (1, True),
        (-1, True),
        (0, False),
        (42, True),
        # float
        (1.0, True),
        (-0.5, True),
        (0.0, False),
        # true strings
        ("true", True),
        ("allow", True),
        ("enable", True),
        ("enabled", True),
        ("yes", True),
        ("1", True),
        ("on", True),
        # false strings
        ("false", False),
        ("block", False),
        ("disable", False),
        ("disabled", False),
        ("no", False),
        ("0", False),
        ("off", False),
        # case-insensitive + whitespace
        ("  TRUE  ", True),
        ("  FALSE  ", False),
        ("On", True),
        ("OFF", False),
    ],
)
def test_raw_to_bool(value: Any, expected: bool | None) -> None:
    """Test raw_to_bool."""

    assert raw_to_bool(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # Non-convertible -> None
        (None, None),
        ([], None),
        ({}, None),
        ("", None),
        ("  ", None),
        ("abc", None),
        ("inf", None),
        ("1e400", None),
        # bool/int passthrough (bool is subclass of int)
        (True, 1),
        (False, 0),
        (42, 42),
        (-5, -5),
        # float truncation
        (3.7, 3),
        (-2.9, -2),
        # non-finite floats -> None
        (float("inf"), None),
        (float("-inf"), None),
        (float("nan"), None),
        # decimal strings
        ("42", 42),
        ("-5", -5),
        # float-string fallback
        ("3.14", 3),
        # whitespace + BOM cleaned
        ("  42  ", 42),
        (_BOM + "42", 42),
    ],
)
def test_raw_to_int(value: Any, expected: int | None) -> None:
    """Test raw_to_int."""

    assert raw_to_int(value) == expected


@pytest.mark.parametrize(
    ("base", "value", "expected"),
    [
        (16, "ff", 255),
        (16, "FF", 255),
        (16, "1f", 31),
        (10, "42", 42),
    ],
)
def test_raw_to_int_base(base: int, value: str, expected: int) -> None:
    """Test raw_to_int with explicit base."""

    assert raw_to_int(value, base=base) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # Non-convertible -> None
        (None, None),
        ([], None),
        ({}, None),
        ("", None),
        ("  ", None),
        ("abc", None),
        # bool/int/float passthrough
        (True, 1.0),
        (False, 0.0),
        (42, 42.0),
        (3.14, 3.14),
        (-5, -5.0),
        # float strings
        ("3.14", 3.14),
        ("-5.5", -5.5),
        ("42", 42.0),
        # whitespace + BOM cleaned
        ("  3.14  ", 3.14),
        (_BOM + "3.14", 3.14),
    ],
)
def test_raw_to_float(value: Any, expected: float | None) -> None:
    """Test raw_to_float."""

    assert raw_to_float(value) == expected


def test_bom_constant() -> None:
    """Ensure _BOM is the correct BOM character."""

    assert chr(0xFEFF) == _BOM
    assert len(_BOM) == 1


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # Non-string inputs -> None
        (None, None),
        (0, None),
        (True, None),
        ([], None),
        # Empty and whitespace-only -> None
        ("", None),
        ("   ", None),
        # BOM-only -> None
        (_BOM, None),
        (_BOM + "   ", None),
        # Clean strings -> unchanged
        ("hello", "hello"),
        ("123", "123"),
        # Whitespace stripped
        ("  hello  ", "hello"),
        ("\t hello \n", "hello"),
        # BOM stripped, then whitespace around content
        (_BOM + "hello", "hello"),
        (_BOM + "  hello  ", "hello"),
    ],
)
def test_raw_to_str(value: Any, expected: str | None) -> None:
    """Test raw_to_str."""

    assert raw_to_str(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2021-01-01   ", datetime(2021, 1, 1)),  # ISO date, trailing space
        ("2021-01-01 00:00:00", datetime(2021, 1, 1)),  # ISO with time
        # RFC-1123 style (fromisoformat fails, strptime path)
        (
            "Mon, 01 Jan 2021 00:00:00 +0000",
            datetime(2021, 1, 1, tzinfo=UTC),
        ),
        # No value -> None
        (None, None),
        ("", None),
        ("  ", None),
        # Non-datetime content -> None
        ("unknown", None),
        ("test", None),
        ("  test  ", None),
    ],
)
def test_raw_to_datetime(value: Any, expected: datetime | None) -> None:
    """Test raw_to_datetime."""

    assert raw_to_datetime(value) == expected


@pytest.mark.parametrize(
    ("value", "delimiter", "expected"),
    [
        (None, " ", []),  # No value
        (1, " ", []),  # Non-string
        ({1: 2}, " ", []),
        ("", " ", []),  # Empty string cleaned to None
        ("   ", " ", []),
        ("test", " ", ["test"]),  # Single token
        ("test1 test2", " ", ["test1", "test2"]),  # Default delimiter
        ("a&#60b&#60c", "&#60", ["a", "b", "c"]),  # Custom delimiter
        ("test1 test2", ";", ["test1 test2"]),  # Delimiter not present
    ],
)
def test_raw_to_str_list(
    value: Any, delimiter: str, expected: list[str]
) -> None:
    """Test raw_to_str_list."""

    assert raw_to_str_list(value, delimiter) == expected
