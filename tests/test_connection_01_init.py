"""Tests for the connection module / Part 1 / Init & Config."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from asusrouter.connection import Connection, generate_credentials
from asusrouter.connection_config import (
    CONNECTION_CONFIG_DEFAULT,
    ARConnectionConfigKey as ARCCKey,
)
from asusrouter.const import (
    DEFAULT_PORT_HTTP,
    DEFAULT_PORT_HTTPS,
    DEFAULT_TIMEOUT,
)
from tests.helpers import (
    TCONST_HOST,
    TCONST_PASS,
    TCONST_USER,
    AsyncPatch,
    ConnectionFactory,
)


@pytest.mark.asyncio
async def test_generate_credentials() -> None:
    """Test the `generate_credentials`."""

    username = TCONST_USER
    password = TCONST_PASS
    payload, headers = generate_credentials(username, password)
    assert payload == "login_authorization=dXNlcjpwYXNz"
    assert headers == {"user-agent": "asusrouter--DUTUtil-"}


class TestConnectionInit:
    """Tests for the Connection class init and config."""

    def _assert_connection(
        self,
        conn: Connection,
        hostname: str,
        username: str,
        password: str,
        port: int | None,
        use_ssl: bool,
        session: Mock | None,
        timeout: int,
        dumpback: Mock | None,
        config: dict[ARCCKey, Any] | None,
        mock_new_session: Mock,
    ) -> None:
        """Test the Connection object."""

        assert conn._hostname == hostname
        assert conn._username == username
        assert conn._password == password
        assert conn.port == port or (
            DEFAULT_PORT_HTTPS if use_ssl else DEFAULT_PORT_HTTP
        )
        if not config:
            config = {}
        for key, value in config.items():
            assert conn.config.get(key) == value
        assert conn.config.get(ARCCKey.USE_SSL) == use_ssl
        assert conn._session == (session or mock_new_session.return_value)
        assert conn._timeout == timeout
        assert conn._dumpback == dumpback
        assert conn._token is None
        assert conn._header is None
        assert conn._connected is False
        assert isinstance(conn._connection_lock, asyncio.Lock)

    @pytest.mark.parametrize(
        (
            "hostname",
            "username",
            "password",
            "port",
            "use_ssl",
            "session",
            "timeout",
            "dumpback",
            "config",
        ),
        [
            (
                TCONST_HOST,
                TCONST_USER,
                TCONST_PASS,
                None,
                False,
                None,
                None,
                None,
                CONNECTION_CONFIG_DEFAULT,
            ),
            (
                TCONST_HOST,
                TCONST_USER,
                TCONST_PASS,
                8080,
                True,
                None,
                None,
                None,
                CONNECTION_CONFIG_DEFAULT,
            ),
            (
                TCONST_HOST,
                TCONST_USER,
                TCONST_PASS,
                8080,
                False,
                Mock(),
                None,
                None,
                CONNECTION_CONFIG_DEFAULT,
            ),
            (
                TCONST_HOST,
                TCONST_USER,
                TCONST_PASS,
                8080,
                True,
                Mock(),
                10,
                Mock(),
                CONNECTION_CONFIG_DEFAULT,
            ),
            (
                "",
                TCONST_USER,
                TCONST_PASS,
                8080,
                True,
                Mock(),
                None,
                Mock(),
                CONNECTION_CONFIG_DEFAULT,
            ),
            (
                TCONST_HOST,
                "",
                TCONST_PASS,
                8080,
                True,
                None,
                10,
                None,
                CONNECTION_CONFIG_DEFAULT,
            ),
            (
                TCONST_HOST,
                TCONST_USER,
                TCONST_PASS,
                -1,
                True,
                None,
                15,
                None,
                CONNECTION_CONFIG_DEFAULT,
            ),
        ],
        ids=[
            "default",
            "custom_port_ssl",
            "custom_session",
            "custom_timeout_dumpback",
            "empty_hostname",
            "empty_username",
            "negative_port",
        ],
    )
    @patch.object(Connection, "_new_session", return_value=Mock())
    def test_init(
        self,
        mock_new_session: Mock,
        hostname: str,
        username: str,
        password: str,
        port: int,
        use_ssl: bool,
        session: Mock | None,
        timeout: int | None,
        dumpback: Mock | None,
        config: dict[ARCCKey, Any] | None,
    ) -> None:
        """Test the initialization of the connection object."""

        # Replace port and use_ssl configs with the ones provided
        if not config:
            config = {}

        config[ARCCKey.PORT] = port or (
            DEFAULT_PORT_HTTPS if use_ssl else DEFAULT_PORT_HTTP
        )
        config[ARCCKey.USE_SSL] = use_ssl

        # Create a Connection
        conn = Connection(
            hostname=hostname,
            username=username,
            password=password,
            port=port,
            use_ssl=use_ssl,
            session=session,
            timeout=timeout,
            dumpback=dumpback,
            config=config,
        )

        # Test the Connection
        self._assert_connection(
            conn,
            hostname=hostname,
            username=username,
            password=password,
            port=port,
            use_ssl=use_ssl,
            session=session,
            timeout=timeout or DEFAULT_TIMEOUT,
            dumpback=dumpback,
            config=config,
            mock_new_session=mock_new_session,
        )

    @patch.object(Connection, "_new_session", return_value=Mock())
    def test_init_multiple_instances(self, mock_new_session: Mock) -> None:
        """Test the initialization of multiple connection objects."""

        # Explicitly set different initial configs
        config1 = {
            ARCCKey.ALLOW_FALLBACK: True,
        }
        config2 = {
            ARCCKey.ALLOW_FALLBACK: False,
        }

        # Create two Connection
        conn1 = Connection(
            hostname="localhost1",
            username="user1",
            password="pass1",
            port=8080,
            use_ssl=True,
            timeout=None,
            config=config1,
        )
        conn2 = Connection(
            hostname="localhost2",
            username="user2",
            password="pass2",
            port=9090,
            use_ssl=False,
            timeout=1,
            config=config2,
        )

        # Test the Connections
        self._assert_connection(
            conn1,
            hostname="localhost1",
            username="user1",
            password="pass1",
            port=8080,
            use_ssl=True,
            session=None,
            timeout=DEFAULT_TIMEOUT,
            dumpback=None,
            config=config1,
            mock_new_session=mock_new_session,
        )
        self._assert_connection(
            conn2,
            hostname="localhost2",
            username="user2",
            password="pass2",
            port=9090,
            use_ssl=False,
            session=None,
            timeout=1,
            dumpback=None,
            config=config2,
            mock_new_session=mock_new_session,
        )

        # Ensure that instances do not interfere with each other
        assert conn1._hostname != conn2._hostname
        assert conn1._username != conn2._username
        assert conn1._password != conn2._password
        assert conn1.port != conn2.port
        assert conn1.config.get(ARCCKey.USE_SSL) != conn2.config.get(
            ARCCKey.USE_SSL
        )
        assert conn1.config.get(ARCCKey.ALLOW_FALLBACK) != conn2.config.get(
            ARCCKey.ALLOW_FALLBACK
        )
        assert conn1._timeout != conn2._timeout

    @pytest.mark.asyncio
    async def test_aenter(
        self,
        connection_factory: ConnectionFactory,
        async_connect: AsyncPatch,
    ) -> None:
        """Test the `__aenter__` method."""

        mock_async_connect = async_connect(Connection)

        # Create a Connection
        connection = connection_factory(port=8080, use_ssl=True)

        # Enter the context manager
        async with connection as conn:
            # Verify that async_connect was called
            mock_async_connect.assert_called_once()

            # Verify that the connection object is returned
            assert conn is connection

    @pytest.mark.asyncio
    async def test_aexit(
        self, connection_factory: ConnectionFactory, async_connect: AsyncPatch
    ) -> None:
        """Test the `__aexit__` method."""

        # Mock the async_connect and async_close methods
        mock_async_connect = async_connect(Connection)
        with patch.object(
            Connection, "async_close", new_callable=AsyncMock
        ) as mock_close:
            # Create a Connection
            connection = connection_factory(port=8080, use_ssl=True)

            # Exit the context manager
            async with connection:
                pass

            # Verify that async_connect was called
            mock_async_connect.assert_called_once()

            # Verify that async_close was called
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_create(self, async_connect: AsyncPatch) -> None:
        """Test the `create` class method."""

        # Mock the async_connect method
        mock_async_connect = async_connect(Connection)

        # Define test parameters
        hostname = TCONST_HOST
        username = TCONST_USER
        password = TCONST_PASS
        port = 8080
        use_ssl = True
        session = Mock()
        timeout = 15
        dumpback = Mock()
        allow_fallback = True
        config = {ARCCKey.ALLOW_FALLBACK: allow_fallback}

        # Call the create method
        connection = await Connection.create(
            hostname=hostname,
            username=username,
            password=password,
            port=port,
            use_ssl=use_ssl,
            session=session,
            timeout=timeout,
            dumpback=dumpback,
            config=config,
        )

        # Verify that async_connect was called
        mock_async_connect.assert_called_once()

        # Verify that the returned object is an instance of Connection
        assert isinstance(connection, Connection)

        # Verify that the connection object is initialized correctly
        assert connection._hostname == hostname
        assert connection._username == username
        assert connection._password == password
        assert connection.port == port
        assert connection.config.get(ARCCKey.USE_SSL) == use_ssl
        assert connection._session == session
        assert connection._timeout == timeout
        assert connection._dumpback == dumpback
        assert connection.config.get(ARCCKey.ALLOW_FALLBACK) == allow_fallback
        assert connection._token is None
        assert connection._header is None
        assert connection._connected is False
        assert isinstance(connection._connection_lock, asyncio.Lock)
