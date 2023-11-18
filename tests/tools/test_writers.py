"""Test AsusRouter writers tools."""

import pytest

from asusrouter.tools import writers


@pytest.mark.parametrize(
    "content, expected",
    [
        ("test", "nvram_get(test);"),
        (["test1", "test2"], "nvram_get(test1);nvram_get(test2);"),
        (None, None),
    ],
)
def test_nvram(content, expected):
    """Test nvram method."""

    assert writers.nvram(content) == expected
