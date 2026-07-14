"""Tests for AsusRouter.__init__."""

from __future__ import annotations

from unittest.mock import Mock

import aiohttp
import pytest

from asusrouter.asusrouter import AsusRouter
from asusrouter.config import ARInstanceConfig
from asusrouter.config.connection import ARConnectionConfigKey as ARCCKey
from asusrouter.connection import Connection
from asusrouter.const import DEFAULT_PORT_HTTP, DEFAULT_PORT_HTTPS
from asusrouter.modules.device.identity import ARDeviceIdentity
from tests.helpers import TCONST_HOST, TCONST_PASS, TCONST_USER


def test_init_connection_is_connection_instance() -> None:
    """_connection is a Connection object after init."""

    router = AsusRouter(
        hostname=TCONST_HOST,
        username=TCONST_USER,
        password=TCONST_PASS,
    )
    assert isinstance(router._connection, Connection)


@pytest.mark.parametrize(
    ("hostname", "username", "password"),
    [
        (TCONST_HOST, TCONST_USER, TCONST_PASS),
        ("192.168.1.1", "root", "hunter2"),
    ],
)
def test_init_connection_credentials(
    hostname: str,
    username: str,
    password: str,
) -> None:
    """Connection receives the correct credentials."""

    router = AsusRouter(
        hostname=hostname, username=username, password=password
    )
    assert router._connection._hostname == hostname
    assert router._connection._username == username
    assert router._connection._password == password


@pytest.mark.parametrize(
    ("port", "use_ssl", "expected_port"),
    [
        (None, False, DEFAULT_PORT_HTTP),
        (None, True, DEFAULT_PORT_HTTPS),
        (8080, False, 8080),
        (8553, True, 8553),
    ],
)
def test_init_connection_port_ssl(
    port: int | None,
    use_ssl: bool,
    expected_port: int,
) -> None:
    """Connection receives the correct port and SSL config."""

    router = AsusRouter(
        hostname=TCONST_HOST,
        username=TCONST_USER,
        password=TCONST_PASS,
        port=port,
        use_ssl=use_ssl,
    )
    assert router._connection.port == expected_port
    assert router._connection.config.get(ARCCKey.USE_SSL) == use_ssl


def test_init_connection_with_external_session() -> None:
    """Provided session is stored; connection does not manage it."""

    mock_session = Mock(spec=aiohttp.ClientSession)
    router = AsusRouter(
        hostname=TCONST_HOST,
        username=TCONST_USER,
        password=TCONST_PASS,
        session=mock_session,
    )
    assert router._connection._session is mock_session
    assert router._connection._manage_session is False


def test_init_connection_no_session_deferred() -> None:
    """No session is created eagerly when none is provided."""

    router = AsusRouter(
        hostname=TCONST_HOST,
        username=TCONST_USER,
        password=TCONST_PASS,
    )
    assert router._connection._session is None
    assert router._connection._manage_session is False


def test_init_state_empty(router: AsusRouter) -> None:
    """State dicts start empty."""

    assert router._data_states == {}


def test_init_description(router: AsusRouter) -> None:
    """Description returns empty ARDeviceIdentity before any data is loaded."""

    assert isinstance(router.description, ARDeviceIdentity)


def test_init_config_instance(router: AsusRouter) -> None:
    """_config is an ARInstanceConfig."""

    assert isinstance(router._config, ARInstanceConfig)
