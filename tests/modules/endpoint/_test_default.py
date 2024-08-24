"""Tests for the default endpoint module."""

from typing import Any, Callable

from asusrouter.tools.readers import read_json_content


def _test_read(read: Callable[[str], dict[str, Any]]):
    """Test read function."""

    # Check if 'read' is the same as 'read_json_content'
    assert read == read_json_content
