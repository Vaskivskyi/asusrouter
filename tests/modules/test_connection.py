"""Tests for the connection module."""

from asusrouter.modules.connection import (
    ConnectionType,
    InternetMode,
    get_connection_type,
    get_internet_mode,
)
import pytest


@pytest.mark.parametrize(
    ("value", "result"),
    [
        # Existing values of InternetMode
        ("allow", InternetMode.ALLOW),
        ("block", InternetMode.BLOCK),
        ("time", InternetMode.TIME),
        # Unknown values of the same type
        ("unknown", InternetMode.UNKNOWN),
        ("", InternetMode.UNKNOWN),
        # Values of the wrong type
        (None, InternetMode.UNKNOWN),
        (1, InternetMode.UNKNOWN),
    ],
)
def test_get_internet_mode(value: str | None, result: InternetMode) -> None:
    """Test get_internet_mode."""

    assert get_internet_mode(value) == result


@pytest.mark.parametrize(
    ("value", "result"),
    [
        # Existing values of ConnectionType
        (0, ConnectionType.WIRED),
        (1, ConnectionType.WLAN_2G),
        (2, ConnectionType.WLAN_5G),
        (3, ConnectionType.WLAN_5G2),
        (4, ConnectionType.WLAN_6G),
        # Unknown values of the same type
        (-1, ConnectionType.WIRED),
        (5, ConnectionType.WIRED),
        # Values of the wrong type
        (None, ConnectionType.WIRED),
        ("", ConnectionType.WIRED),
        # Special cases which would still work
        (1.0, ConnectionType.WLAN_2G),
        (2.3, ConnectionType.WLAN_5G),
    ],
)
def test_get_connection_type(
    value: int | None, result: ConnectionType
) -> None:
    """Test get_connection_type."""

    assert get_connection_type(value) == result
