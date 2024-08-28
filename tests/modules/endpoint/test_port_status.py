"""Tests for the Port Status endpoint module."""

from asusrouter.modules.endpoint.port_status import read

from ._test_default import _test_read


def test_read():
    """Test read function."""

    _test_read(read)
