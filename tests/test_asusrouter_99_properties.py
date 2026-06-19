"""Tests for the asusrouter module / Part 99 / Properties."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from asusrouter.asusrouter import AsusRouter
from asusrouter.const import DEFAULT_PORT_HTTP, DEFAULT_PORT_HTTPS

TCONST_HOST = "router.local"
TCONST_USER = "admin"
TCONST_PASS = "password"


@pytest.mark.parametrize("connected", [True, False])
def test_connected(router: AsusRouter, connected: bool) -> None:
    """Test the connected property."""

    router._connection = Mock()
    router._connection.connected = connected
    assert router.connected is connected


def test_connected_not_connected_yet(router: AsusRouter) -> None:
    """Test the connected property before login."""

    assert router.connected is False


def test_config(router: AsusRouter) -> None:
    """Test the config property."""

    assert router.config == router._config


@pytest.mark.parametrize(
    ("port", "use_ssl", "expected_scheme", "expected_port"),
    [
        (None, False, "http", DEFAULT_PORT_HTTP),
        (None, True, "https", DEFAULT_PORT_HTTPS),
        (8080, False, "http", 8080),
        (8553, True, "https", 8553),
    ],
)
def test_webpanel(
    port: int | None,
    use_ssl: bool,
    expected_scheme: str,
    expected_port: int,
) -> None:
    """Test the webpanel property returns the correct URL."""

    router = AsusRouter(
        hostname=TCONST_HOST,
        username=TCONST_USER,
        password=TCONST_PASS,
        port=port,
        use_ssl=use_ssl,
    )
    assert (
        router.webpanel == f"{expected_scheme}://{TCONST_HOST}:{expected_port}"
    )
