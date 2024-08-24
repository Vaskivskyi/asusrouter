"""Tests for the Hook endpoint module."""

from asusrouter.modules.endpoint.hook import read

from ._test_default import _test_read


def test_read():
    """Test read function."""

    _test_read(read)
