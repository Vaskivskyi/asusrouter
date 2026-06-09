"""Tests for the Port Status endpoint module."""

from __future__ import annotations

from asusrouter.modules.endpoint.port_status import read

from ._test_default import _test_read


def test_read():
    """Test read function."""

    _test_read(read)
