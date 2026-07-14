"""Test AusRouter converters tools."""

from __future__ import annotations

from datetime import datetime

import pytest

from asusrouter.tools import converters


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
