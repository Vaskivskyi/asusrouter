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
        ({}, []),
        ({ARSupportValue.CONNECTION_HTTPS: 1}, [ARConnection.HTTPS]),
        ({ARSupportValue.CONNECTION_SSH: 1}, [ARConnection.SSH]),
        (
            {
                ARSupportValue.CONNECTION_HTTPS: 1,
                ARSupportValue.CONNECTION_SSH: 1,
            },
            [ARConnection.HTTPS, ARConnection.SSH],
        ),
        (
            {
                ARSupportValue.CONNECTION_HTTPS: 0,
                ARSupportValue.CONNECTION_SSH: 0,
            },
            [],
        ),
        (
            {
                ARSupportValue.CONNECTION_HTTPS: True,
                ARSupportValue.CONNECTION_SSH: False,
            },
            [ARConnection.HTTPS],
        ),
        (
            {
                ARSupportValue.CONNECTION_HTTPS: "0",
                ARSupportValue.CONNECTION_SSH: "1",
            },
            [ARConnection.SSH],
        ),
        # Not a dict
        ("not_a_dict", []),
    ],
)
def test_translate_connection(
    data: dict[str, Any], expected: list[ARConnection]
) -> None:
    """Test translate_connection returns correct connection types."""

    result = translate_connection(data)
    assert set(result) == set(expected)
