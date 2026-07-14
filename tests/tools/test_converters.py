"""Test AusRouter converters tools."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from asusrouter.tools import converters


def test_flatten_dict() -> None:
    """Test flatten_dict method."""

    nested_dict: dict[str, Any] = {"a": {"b": {"c": 1}}, "d": {"e": 2}}
    expected_output: dict[str, Any] = {"a_b_c": 1, "d_e": 2}
    assert converters.flatten_dict(nested_dict) == expected_output

    # Test with None input
    assert converters.flatten_dict(None) is None

    # Test with non-dict input
    assert converters.flatten_dict("not a dict") == {}  # type: ignore[arg-type]

    # Test with exclude parameter
    nested_dict = {"a": {"b": {"c": 1}}, "d": 2}
    expected_output = {"a_b": {"c": 1}, "d": 2}
    assert converters.flatten_dict(nested_dict, exclude="b") == expected_output


def test_nvram_get() -> None:
    """Test nvram_get method."""

    # Test with empty input
    assert converters.nvram_get(None) is None

    # Test with string input
    assert converters.nvram_get("test") == [("nvram_get", "test")]

    # Test with list input
    assert converters.nvram_get(["test1", "test2"]) == [
        ("nvram_get", "test1"),
        ("nvram_get", "test2"),
    ]

    # Test with other input
    assert converters.nvram_get(123) == [("nvram_get", "123")]  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("content", "result"),
    [
        ("2021-01-01   ", datetime(2021, 1, 1)),  # Date content
        ("2021-01-01 00:00:00", datetime(2021, 1, 1)),
        (None, None),  # None content
        ("", None),
        ("  ", None),
        ("unknown", None),  # Non-datetime content
        ("test", None),
        ("  test  ", None),
    ],
)
def test_safe_datetime(content: str | None, result: datetime | None) -> None:
    """Test safe_datetime method."""

    assert converters.safe_datetime(content) == result


@pytest.mark.parametrize(
    ("content", "delimiter", "result"),
    [
        (None, None, []),  # Not a string
        (1, None, []),
        ({1: 2}, None, []),
        ("test", None, ["test"]),  # String
        ("test1 test2", None, ["test1", "test2"]),
        ("test1 test2", ";", ["test1 test2"]),  # Wrong delimiter
    ],
)
def test_safe_list_from_string(
    content: str | None, delimiter: str, result: list[str]
) -> None:
    """Test safe_list_from_string method."""

    assert converters.safe_list_from_string(content, delimiter) == result


@patch("asusrouter.tools.converters.datetime")
def test_safe_time_from_delta(mock_datetime: MagicMock) -> None:
    """Test safe_time_from_delta method."""

    # Set up the mock to return a specific datetime when now() is called
    mock_datetime.now.return_value = datetime(2023, 8, 15, tzinfo=UTC)

    result = converters.safe_time_from_delta(
        "48:00:15"
    )  # 48 hours, 15 seconds
    expected = datetime(2023, 8, 12, 23, 59, 45, tzinfo=UTC)
    assert result == expected


def test_safe_timedelta_long() -> None:
    """Test safe_timedelta_long method."""

    # Test with valid string
    assert converters.safe_timedelta_long("01:30:15   ") == timedelta(
        hours=1, minutes=30, seconds=15
    )
    assert converters.safe_timedelta_long("   30:15:27") == timedelta(
        hours=30, minutes=15, seconds=27
    )

    # Test with invalid string
    assert converters.safe_timedelta_long("invalid") == timedelta()

    # Test with None
    assert converters.safe_timedelta_long(None) == timedelta()


@pytest.mark.parametrize(
    ("used", "total", "result"),
    [
        (5, 10, 50.0),  # normal usage
        (10, 10, 100.0),  # normal usage
        (3, 9, 33.33),  # round to 2 decimals
        (-1, 2, 0.0),  # negative usage not allowed
        (1, -2, 0.0),  # negative usage not allowed
        (-1, -1, 100.0),  # both negative values result in positive usage
        (1, 0, 0.0),  # zero total usage not allowed
        (0, 0, 0.0),  # zero total usage not allowed
    ],
)
def test_safe_usage(used: float, total: float, result: float) -> None:
    """Test safe_usage method."""

    assert converters.safe_usage(used, total) == result


@pytest.mark.parametrize(
    ("used", "total", "prev_used", "prev_total", "result"),
    [
        (10, 20, 5, 10, 50.0),  # normal usage
        (10, 20, 10, 20, 0.0),  # no usage
        (6, 18, 3, 9, 33.33),  # round to 2 decimals
        (
            5,
            20,
            10,
            10,
            0.0,
        ),  # invalid case when current used is less than previous
        (
            10,
            20,
            5,
            25,
            0.0,
        ),  # invalid case when current total is less than previous
        (
            5,
            10,
            10,
            20,
            0.0,
        ),  # invalid case when current values are less than previous
    ],
)
def test_safe_usage_historic(
    used: float,
    total: float,
    prev_used: float,
    prev_total: float,
    result: float,
) -> None:
    """Test safe_usage_historic method."""

    assert (
        converters.safe_usage_historic(used, total, prev_used, prev_total)
        == result
    )
