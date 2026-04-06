"""Tests for the support connection module."""

from typing import Any

import pytest

from asusrouter.modules.support.connection import (
    ARSupportConnection,
    translate_connection,
)
from asusrouter.modules.support.flag import ARSupportValue


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, []),
        ({ARSupportValue.CONNECTION_HTTPS: 1}, [ARSupportConnection.HTTPS]),
        ({ARSupportValue.CONNECTION_SSH: 1}, [ARSupportConnection.SSH]),
        (
            {
                ARSupportValue.CONNECTION_HTTPS: 1,
                ARSupportValue.CONNECTION_SSH: 1,
            },
            [ARSupportConnection.HTTPS, ARSupportConnection.SSH],
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
            [ARSupportConnection.HTTPS],
        ),
        (
            {
                ARSupportValue.CONNECTION_HTTPS: "0",
                ARSupportValue.CONNECTION_SSH: "1",
            },
            [ARSupportConnection.SSH],
        ),
        # Not a dict
        ("not_a_dict", []),
    ],
)
def test_translate_connection(
    data: dict[str, Any], expected: list[ARSupportConnection]
) -> None:
    """Test translate_connection returns correct connection types."""

    result = translate_connection(data)
    assert set(result) == set(expected)
