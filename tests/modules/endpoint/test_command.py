"""Test AsusRouter command endpoint module."""

from asusrouter.modules.endpoint.command import read

from ._test_default import _test_read


def test_read():
    """Test read function."""

    _test_read(read)
