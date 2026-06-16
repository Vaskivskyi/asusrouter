"""Tests for the support connection module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.connection_v2 import ARConnection
from asusrouter.modules.support.connection import translate_connection
from asusrouter.modules.support.flag import ARSupportValue


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.CONNECTION_HTTPS.value: 1}, [ARConnection.HTTPS]),
        ({ARSupportValue.CONNECTION_SSH.value: 1}, [ARConnection.SSH]),
        ({}, []),
    ],
)
def test_translate_connection(
    data: dict[str, Any], expected: list[ARConnection]
) -> None:
    """Test translate_connection returns correct connection types."""

    assert translate_connection(data) == expected
