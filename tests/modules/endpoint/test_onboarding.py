"""Tests for the onboarding endpoint module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter import AsusData
from asusrouter.modules.endpoint.onboarding import (
    CONNECTION_TYPE,
    process,
    process_connection,
    read,
)
from asusrouter.tools.readers import read_js_variables

DATA_ALLCLIENTLIST = [
    {
        "00:aa:11:bb:22:cc": {
            "2G": {"00:aa:11:bb:22:dd": {"ip": "192.168.1.12", "rssi": -34}}
        }
    }
]

RESULT_ALLCLIENTLIST = {
    "00:aa:11:bb:22:dd": {
        "connection_type": 1,
        "guest": 0,
        "ip": "192.168.1.12",
        "mac": "00:aa:11:bb:22:dd",
        "node": "00:aa:11:bb:22:cc",
        "online": True,
        "rssi": -34,
    }
}


def test_read() -> None:
    """Test read function."""

    # Check if 'read' is the same as 'read_js_variables'
    assert read == read_js_variables


@pytest.mark.parametrize(
    ("data_allclientlist", "result_allclientlist"),
    [
        (DATA_ALLCLIENTLIST, RESULT_ALLCLIENTLIST),
        (None, {}),
    ],
    ids=["with_clients", "no_clients"],
)
def test_process(
    data_allclientlist: list[dict[str, Any]] | None,
    result_allclientlist: dict[str, dict[str, Any]],
) -> None:
    """Process builds the client list keyed by AsusData.CLIENTS."""

    data: dict[str, Any] = {}
    if data_allclientlist is not None:
        data["get_allclientlist"] = data_allclientlist

    result = process(data)

    assert result == {AsusData.CLIENTS: result_allclientlist}


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        # An empty string
        ("", {}),
        # Data for a wired connection
        ("wired_mac", {"connection_type": 0, "guest": 0}),
        # Data for a wireless guest connection
        (
            "type_1",
            {"connection_type": CONNECTION_TYPE.get("type") or 0, "guest": 1},
        ),
        # Wrong data
        (None, {}),
        (123, {}),
    ],
)
def test_process_connection(
    data: str | None, expected: dict[str, int]
) -> None:
    """Test process_connection function."""

    result = process_connection(data)
    assert result == expected
