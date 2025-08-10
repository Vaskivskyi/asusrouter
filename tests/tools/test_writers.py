"""Test AsusRouter writers tools."""

from asusrouter.tools import writers
import pytest


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("test", "nvram_get(test);"),
        (["test1", "test2"], "nvram_get(test1);nvram_get(test2);"),
        (None, None),
    ],
)
def test_nvram(content: str | list[str] | None, expected: str | None) -> None:
    """Test nvram method."""

    assert writers.nvram(content) == expected
