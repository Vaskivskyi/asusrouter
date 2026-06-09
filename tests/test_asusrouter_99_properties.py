"""Tests for the asusrouter module / Part 99 / Properties."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from asusrouter.asusrouter import AsusRouter
from asusrouter.const import DEFAULT_PORT_HTTP, DEFAULT_PORT_HTTPS


@pytest.mark.parametrize("connected", [True, False])
def test_connected(router: AsusRouter, connected: bool) -> None:
    """Test the connected property."""

    router._connection = Mock()
    router._connection.connected = connected
    assert router.connected is connected


def test_connected_no_connection(router: AsusRouter) -> None:
    """Test the connected property when no connection is established."""

    assert router.connected is False


def test_config(router: AsusRouter) -> None:
    """Test the config property."""

    assert router.config == router._config


@pytest.mark.parametrize(
    ("port", "use_ssl"),
    [
        (None, True),
        (None, False),
        (8553, True),
        (8080, False),
    ],
)
def test_webpanel(router: AsusRouter, port: int | None, use_ssl: bool) -> None:
    """Test the webpanel property."""

    router._port = port
    router._use_ssl = use_ssl

    assert router.webpanel == (
        f"https://{router._hostname}:{port or DEFAULT_PORT_HTTPS}"
        if use_ssl
        else f"http://{router._hostname}:{port or DEFAULT_PORT_HTTP}"
    )


def test_webpanel_with_connection(router: AsusRouter) -> None:
    """Test the webpanel property when connected."""

    webpanel = "webpanel"

    router._connection = Mock()
    router._connection.webpanel = webpanel

    assert router.webpanel == webpanel
