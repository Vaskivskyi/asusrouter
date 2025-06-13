"""Tests for the connection module."""

import asyncio
import json
from typing import Any, Optional, Tuple
from unittest.mock import AsyncMock, Mock, patch

import aiohttp

import pytest
from asusrouter.connection import Connection, generate_credentials
from asusrouter.const import DEFAULT_TIMEOUT, USER_AGENT, RequestType
from asusrouter.error import (
    AsusRouter404Error,
    AsusRouterAccessError,
    AsusRouterConnectionError,
    AsusRouterError,
    AsusRouterLogoutError,
    AsusRouterTimeoutError,
)
from asusrouter.modules.endpoint import EndpointService


@pytest.mark.asyncio
async def test_generate_credentials() -> None:
    """Test the `generate_credentials`."""

    username = "user"
    password = "pass"
    payload, headers = generate_credentials(username, password)
    assert payload == "login_authorization=dXNlcjpwYXNz"
    assert headers == {"user-agent": "asusrouter--DUTUtil-"}


class TestConnection:
    def _assert_connection(
        self,
        conn: Connection,
        hostname: str,
        username: str,
        password: str,
        port: Optional[int],
        use_ssl: bool,
        session: Optional[Mock],
        timeout: int,
        dumpback: Optional[Mock],
        mock_new_session: Mock,
    ) -> None:
        """Test the Connection object."""

        assert conn._hostname == hostname
        assert conn._username == username
        assert conn._password == password
        assert conn._port == (port or (8443 if use_ssl else 80))
        assert conn._ssl == use_ssl
        assert conn._session == (session or mock_new_session.return_value)
        assert conn._timeout == timeout
        assert conn._dumpback == dumpback
        assert conn._token is None
        assert conn._header is None
        assert conn._connected is False
        assert isinstance(conn._connection_lock, asyncio.Lock)

    @pytest.mark.parametrize(
        "hostname, username, password, port, use_ssl, session, timeout,"
        "dumpback",
        [
            ("localhost", "user", "pass", None, False, None, None, None),
            ("localhost", "user", "pass", 8080, True, None, None, None),
            ("localhost", "user", "pass", 8080, False, Mock(), None, None),
            ("localhost", "user", "pass", 8080, True, Mock(), 10, Mock()),
            ("", "user", "pass", 8080, True, Mock(), None, Mock()),
            ("localhost", "", "pass", 8080, True, None, 10, None),
            ("localhost", "user", "pass", -1, True, None, 15, None),
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
        session: Optional[Mock],
        timeout: Optional[int],
        dumpback: Optional[Mock],
    ) -> None:
        """Test the initialization of the connection object."""

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
            mock_new_session=mock_new_session,
        )

    @patch.object(Connection, "_new_session", return_value=Mock())
    def test_init_multiple_instances(self, mock_new_session: Mock) -> None:
        """Test the initialization of multiple connection objects."""

        # Create two Connection
        conn1 = Connection(
            hostname="localhost1",
            username="user1",
            password="pass1",
            port=8080,
            use_ssl=True,
            timeout=None,
        )
        conn2 = Connection(
            hostname="localhost2",
            username="user2",
            password="pass2",
            port=9090,
            use_ssl=False,
            timeout=1,
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
            mock_new_session=mock_new_session,
        )

        # Ensure that instances do not interfere with each other
        assert conn1._hostname != conn2._hostname
        assert conn1._username != conn2._username
        assert conn1._password != conn2._password
        assert conn1._port != conn2._port
        assert conn1._ssl != conn2._ssl
        assert conn1._timeout != conn2._timeout

    @pytest.mark.asyncio
    async def test_aenter(self) -> None:
        """Test the `__aenter__` method."""

        with patch.object(
            Connection, "async_connect", new_callable=AsyncMock
        ) as mock_connect:
            # Create a Connection
            connection = Connection(
                hostname="localhost",
                username="user",
                password="pass",
                port=8080,
                use_ssl=True,
            )

            # Enter the context manager
            async with connection as conn:
                # Verify that async_connect was called
                mock_connect.assert_called_once()

                # Verify that the connection object is returned
                assert conn is connection

    @pytest.mark.asyncio
    async def test_aexit(self) -> None:
        """Test the `__aexit__` method."""

        # Mock the async_connect and async_close methods
        with (
            patch.object(
                Connection, "async_connect", new_callable=AsyncMock
            ) as mock_connect,
            patch.object(
                Connection, "async_close", new_callable=AsyncMock
            ) as mock_close,
        ):
            # Create a Connection
            connection = Connection(
                hostname="localhost",
                username="user",
                password="pass",
                port=8080,
                use_ssl=True,
            )

            # Exit the context manager
            async with connection:
                pass

            # Verify that async_connect was called
            mock_connect.assert_called_once()

            # Verify that async_close was called
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_create(self) -> None:
        """Test the `create` class method."""

        # Mock the async_connect method
        with patch.object(
            Connection, "async_connect", new_callable=AsyncMock
        ) as mock_connect:
            # Define test parameters
            hostname = "localhost"
            username = "user"
            password = "pass"
            port = 8080
            use_ssl = True
            session = Mock()
            timeout = 15
            dumpback = Mock()

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
            )

            # Verify that async_connect was called
            mock_connect.assert_called_once()

            # Verify that the returned object is an instance of Connection
            assert isinstance(connection, Connection)

            # Verify that the connection object is initialized correctly
            assert connection._hostname == hostname
            assert connection._username == username
            assert connection._password == password
            assert connection._port == port
            assert connection._ssl == use_ssl
            assert connection._session == session
            assert connection._timeout == timeout
            assert connection._dumpback == dumpback
            assert connection._token is None
            assert connection._header is None
            assert connection._connected is False
            assert isinstance(connection._connection_lock, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_new_session(self) -> None:
        """Test the `_new_session` method."""

        # Create a Connection
        connection = Connection(
            hostname="localhost",
            username="user",
            password="pass",
            timeout=30,
        )

        # Mock aiohttp.ClientSession and aiohttp.TCPConnector
        with (
            patch("aiohttp.ClientSession") as mock_client_session,
            patch("aiohttp.TCPConnector") as mock_tcp_connector,
            patch(
                "asusrouter.connection.get_cookie_jar",
            ) as mock_get_cookie_jar,
        ):
            # Use a Mock for the cookie jar
            mock_cookie_jar = Mock()
            mock_get_cookie_jar.return_value = mock_cookie_jar

            # Call _new_session
            session = connection._new_session()

            # Verify that _manage_session is set to True
            assert connection._manage_session is True

            # Verify that aiohttp.TCPConnector was called
            # with the correct SSL setting
            mock_tcp_connector.assert_called_once_with(
                ssl=connection._verify_ssl
            )

            # Verify that aiohttp.ClientSession was called
            # with the correct timeout and cookie jar
            mock_client_session.assert_called_once_with(
                connector=mock_tcp_connector.return_value,
                cookie_jar=mock_cookie_jar,
                timeout=aiohttp.ClientTimeout(total=connection._timeout),
            )

            # Verify that the returned session is the mocked session
            assert session == mock_client_session.return_value

    @pytest.mark.asyncio
    async def test_async_close(self) -> None:
        """Test the `async_close` method."""

        # Create a Connection
        connection = Connection(
            hostname="localhost",
            username="user",
            password="pass",
        )

        # Mock the session
        mock_session = AsyncMock()
        connection._session = mock_session
        connection._manage_session = True

        # Case 1: Session is not closed
        mock_session.closed = False
        await connection.async_close()
        mock_session.close.assert_awaited_once()

        # Case 2: Session is already closed
        mock_session.reset_mock()
        mock_session.closed = True
        await connection.async_close()
        mock_session.close.assert_not_awaited()

        # Case 3: _manage_session is False
        connection._manage_session = False
        mock_session.reset_mock()
        await connection.async_close()
        mock_session.close.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_async_connect(self) -> None:
        """Test the `async_connect` method."""

        # Create a Connection
        connection = Connection(
            hostname="localhost",
            username="user",
            password="pass",
            timeout=30,
        )

        # Mock _async_connect_with_lock
        with patch.object(
            connection, "_async_connect_with_lock", new_callable=AsyncMock
        ) as mock_connect_with_lock:
            # Case 1: Connection succeeds
            mock_connect_with_lock.return_value = True
            result = await connection.async_connect()
            mock_connect_with_lock.assert_awaited_once_with(None)
            assert result is True

            # Case 2: Connection times out
            mock_connect_with_lock.reset_mock()
            mock_connect_with_lock.side_effect = asyncio.TimeoutError
            result = await connection.async_connect()
            mock_connect_with_lock.assert_awaited_once_with(None)
            assert result is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "connected, send_request_result, send_request_side_effect,"
        "expected_result, expected_exception, exception_message",
        [
            # Case 1: Already connected
            (True, None, None, True, None, None),
            # Case 2: Successful connection
            (
                False,
                (200, {}, '{"asus_token": "test_token"}'),
                None,
                True,
                None,
                None,
            ),
            # Case 3: AsusRouterAccessError occurs
            (
                False,
                None,
                AsusRouterAccessError("Access denied"),
                None,
                AsusRouterAccessError,
                "Cannot access EndpointService.LOGIN. "
                "Failed in `async_connect`",
            ),
            # Case 4: Unexpected error occurs
            (
                False,
                None,
                Exception("Unexpected error"),
                None,
                Exception,
                "Unexpected error",
            ),
            # Case 5: AsusRouterError occurs
            (
                False,
                None,
                AsusRouterError("Generic AsusRouter error"),
                None,
                AsusRouterError,
                "Generic AsusRouter error",
            ),
            # Case 6: No token received
            (
                False,
                (200, {}, '{"invalid_key": "no_token"}'),
                None,
                False,
                None,
                None,
            ),
        ],
    )
    async def test_async_connect_with_lock(
        self,
        connected: bool,
        send_request_result: Optional[tuple[int, Any, str]],
        send_request_side_effect: Optional[Exception],
        expected_result: Optional[bool],
        expected_exception: Optional[type[BaseException]],
        exception_message: Optional[str],
    ) -> None:
        """Test `_async_connect_with_lock` with parameterized scenarios."""

        # Create a Connection
        connection = Connection(
            hostname="localhost",
            username="user",
            password="pass",
        )

        # Set the initial connection state
        connection._connected = connected

        # Mock the `_send_request` method
        with patch.object(
            connection, "_send_request", new_callable=AsyncMock
        ) as mock_send_request:
            # Configure the mock based on the test case
            if send_request_side_effect:
                mock_send_request.side_effect = send_request_side_effect
            else:
                mock_send_request.return_value = send_request_result

            if expected_exception:
                # Verify that the expected exception is raised
                with pytest.raises(
                    expected_exception, match=exception_message
                ):
                    await connection._async_connect_with_lock()
            else:
                # Call `_async_connect_with_lock`
                result = await connection._async_connect_with_lock()

                # Verify the result
                assert result == expected_result

                # Verify that `_send_request` was called
                # if not already connected
                if not connected:
                    mock_send_request.assert_called_once_with(
                        EndpointService.LOGIN,
                        "login_authorization=dXNlcjpwYXNz",
                        {"user-agent": USER_AGENT},
                    )
                else:
                    mock_send_request.assert_not_called()

            # Additional assertions for successful connection
            if (
                not connected
                and not expected_exception
                and send_request_result
            ):
                if "asus_token" in json.loads(send_request_result[2]):
                    assert connection._connected is True
                    assert connection._token == "test_token"
                    assert connection._header == {
                        "user-agent": USER_AGENT,
                        "cookie": "asus_token=test_token",
                    }
                else:
                    assert connection._connected is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "connected, send_request_side_effect, expected_result,"
        "reset_connection_called",
        [
            # Case 1: Logout error is the correct result
            (True, AsusRouterLogoutError("Session is logged out"), True, True),
            # Case 2: Already disconnected
            (False, None, True, False),
            # Case X: Random results
            (True, None, False, False),
            (True, AsusRouterError("Generic error"), False, False),
        ],
    )
    async def test_async_disconnect(
        self,
        connected: bool,
        send_request_side_effect: Optional[Exception],
        expected_result: bool,
        reset_connection_called: bool,
    ) -> None:
        """Test the `async_disconnect` method with parameterized scenarios."""

        # Create a Connection
        connection = Connection(
            hostname="localhost",
            username="user",
            password="pass",
        )

        # Set the initial connection state
        connection._connected = connected

        # Mock the `_send_request` and `reset_connection` methods
        with (
            patch.object(
                connection, "_send_request", new_callable=AsyncMock
            ) as mock_send_request,
            patch.object(
                connection, "reset_connection", new_callable=Mock
            ) as mock_reset_connection,
        ):
            # Configure the mock for `_send_request`
            if send_request_side_effect:
                mock_send_request.side_effect = send_request_side_effect
            else:
                mock_send_request.return_value = None

            # Call `async_disconnect`
            result = await connection.async_disconnect()

            # Verify the result
            assert result == expected_result

            # Verify `_send_request` was called only if connected
            if connected:
                mock_send_request.assert_called_once_with(
                    EndpointService.LOGOUT
                )
            else:
                mock_send_request.assert_not_called()

            # Verify `reset_connection` was called if expected
            if reset_connection_called:
                mock_reset_connection.assert_called_once()
            else:
                mock_reset_connection.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "resp_status, resp_headers, resp_content, make_request_side_effect,"
        "expected_exception, exception_message",
        [
            # Case 1: Successful request
            (200, {"header": "value"}, '{"key": "value"}', None, None, None),
            # Case 2: 404 error
            (
                404,
                {},
                "",
                None,
                AsusRouter404Error,
                "Endpoint EndpointService.LOGIN not found",
            ),
            # Case 3: Non-200 status code
            (
                403,
                {},
                "",
                None,
                AsusRouterAccessError,
                "Cannot access EndpointService.LOGIN, status 403",
            ),
            # Case 4: Access error in content
            (
                200,
                {},
                '{"error_status": "8"}',
                None,
                AsusRouterAccessError,
                "Access error",
            ),
            # Case 5: Connection error (ClientConnectorError)
            (
                None,
                None,
                None,
                aiohttp.ClientConnectorError(Mock(), Mock()),
                AsusRouterConnectionError,
                "Cannot connect to `localhost` on port `80`.",
            ),
            # Case 6: Connection error (ClientConnectionError)
            (
                None,
                None,
                None,
                aiohttp.ClientConnectionError("Connection error"),
                AsusRouterConnectionError,
                r"Connection error",
            ),
            # Case 7: Connection error (ClientOSError)
            (
                None,
                None,
                None,
                aiohttp.ClientOSError("OS error"),
                AsusRouterConnectionError,
                r"OS error",
            ),
            # Case 8: Unexpected error
            (
                None,
                None,
                None,
                Exception("Unexpected error"),
                Exception,
                "Unexpected error",
            ),
            # Case 9: asyncio.TimeoutError
            (
                None,
                None,
                None,
                asyncio.TimeoutError("operation timed out"),
                AsusRouterTimeoutError,
                r"Data cannot be retrieved due to an asyncio error\. "
                r"Connection failed: operation timed out",
            ),
            # Case 10: asyncio.CancelledError
            (
                None,
                None,
                None,
                asyncio.CancelledError("operation cancelled"),
                AsusRouterTimeoutError,
                r"Data cannot be retrieved due to an asyncio error\. "
                r"Connection failed: operation cancelled",
            ),
        ],
    )
    async def test_send_request(
        self,
        resp_status: Optional[int],
        resp_headers: Optional[dict[str, str]],
        resp_content: Optional[str],
        make_request_side_effect: Optional[Exception],
        expected_exception: Optional[type[BaseException]],
        exception_message: Optional[str],
    ) -> None:
        """Test the `_send_request` method with parameterized scenarios."""

        # Create a Connection
        connection = Connection(
            hostname="localhost",
            username="user",
            password="pass",
        )

        # Mock the _make_request method
        with (
            patch.object(
                connection, "_make_request", new_callable=AsyncMock
            ) as mock_make_request,
            patch(
                "asusrouter.connection.handle_access_error"
            ) as mock_handle_access_error,
            patch.object(
                connection, "reset_connection", new_callable=Mock
            ) as mock_reset_connection,
        ):
            # Configure the mock for _make_request
            if make_request_side_effect:
                mock_make_request.side_effect = make_request_side_effect
            else:
                mock_make_request.return_value = (
                    resp_status,
                    resp_headers,
                    resp_content,
                )

            # Configure handle_access_error to raise an exception if called
            if resp_content and "error_status" in resp_content:
                mock_handle_access_error.side_effect = AsusRouterAccessError(
                    "Access error"
                )

            if expected_exception:
                with pytest.raises(
                    expected_exception, match=exception_message
                ):
                    await connection._send_request(EndpointService.LOGIN)
            else:
                result = await connection._send_request(EndpointService.LOGIN)
                assert result == (resp_status, resp_headers, resp_content)

            # Verify _make_request was called with expected parameters
            mock_make_request.assert_called_once_with(
                EndpointService.LOGIN, None, None, RequestType.POST
            )

            # Verify handle_access_error was called if error_status
            # in content, else not
            if resp_content and "error_status" in resp_content:
                mock_handle_access_error.assert_called_once_with(
                    EndpointService.LOGIN,
                    resp_status,
                    resp_headers,
                    resp_content,
                )
            else:
                mock_handle_access_error.assert_not_called()

            # For ClientConnectorError, reset_connection is expected,
            # but for asyncio.TimeoutError or CancelledError we do not
            # call reset_connection.
            if make_request_side_effect and isinstance(
                make_request_side_effect, aiohttp.ClientConnectorError
            ):
                mock_reset_connection.assert_called_once()
            else:
                mock_reset_connection.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "connected, connect_result, send_request_result,"
        "send_request_side_effect, expected_exception, exception_message",
        [
            # Case 1: Already connected, successful request
            (
                True,
                None,
                (200, {"header": "value"}, '{"key": "value"}'),
                None,
                None,
                None,
            ),
            # Case 2: Not connected, successful connection, successful request
            (
                False,
                True,
                (200, {"header": "value"}, '{"key": "value"}'),
                None,
                None,
                None,
            ),
            # Case 3: Not connected, connection fails
            (
                False,
                False,
                None,
                None,
                AsusRouterTimeoutError,
                "Data cannot be retrieved. Connection failed",
            ),
            # Case 4: Already connected, request fails
            (
                True,
                None,
                None,
                AsusRouterAccessError("Access denied"),
                AsusRouterAccessError,
                "Access denied",
            ),
        ],
    )
    async def test_async_query(
        self,
        connected: bool,
        connect_result: Optional[bool],
        send_request_result: Optional[Tuple[int, dict[str, str], str]],
        send_request_side_effect: Optional[Exception],
        expected_exception: Optional[type[BaseException]],
        exception_message: Optional[str],
    ) -> None:
        """Test the `async_query` method with parameterized scenarios."""

        # Create a Connection
        connection = Connection(
            hostname="localhost",
            username="user",
            password="pass",
        )

        # Set the initial connection state
        connection._connected = connected

        # Mock the `async_connect` and `_send_request` methods
        with (
            patch.object(
                connection, "async_connect", new_callable=AsyncMock
            ) as mock_async_connect,
            patch.object(
                connection, "_send_request", new_callable=AsyncMock
            ) as mock_send_request,
        ):
            # Configure the mock for `async_connect`
            if connect_result is not None:
                mock_async_connect.return_value = connect_result

            # Configure the mock for `_send_request`
            if send_request_side_effect:
                mock_send_request.side_effect = send_request_side_effect
            else:
                mock_send_request.return_value = send_request_result

            if not connected and connect_result:
                # Simulate successful connection by setting `_connected`
                # to True
                mock_async_connect.side_effect = lambda: setattr(
                    connection, "_connected", True
                )

            if expected_exception:
                # Verify that the expected exception is raised
                with pytest.raises(
                    expected_exception, match=exception_message
                ):
                    await connection.async_query(EndpointService.LOGIN)
            else:
                # Call `async_query`
                result = await connection.async_query(EndpointService.LOGIN)

                # Verify the result
                assert result == send_request_result

            # Verify `async_connect` was called if not connected
            if not connected:
                mock_async_connect.assert_called_once()
            else:
                mock_async_connect.assert_not_called()

            # Verify `_send_request` was called
            if connected or (not connected and connect_result):
                mock_send_request.assert_called_once_with(
                    EndpointService.LOGIN, None, None, RequestType.POST
                )
            else:
                mock_send_request.assert_not_called()

    @pytest.mark.parametrize(
        "connected, token, header, expected_connected, expected_token,"
        "expected_header",
        [
            # Case 1: Connection is active
            (
                True,
                "test_token",
                {"user-agent": "test-agent"},
                False,
                None,
                None,
            ),
            # Case 2: Connection is already inactive
            (
                False,
                "test_token",
                {"user-agent": "test-agent"},
                False,
                "test_token",
                {"user-agent": "test-agent"},
            ),
        ],
    )
    def test_reset_connection(
        self,
        connected: bool,
        token: Optional[str],
        header: Optional[dict[str, str]],
        expected_connected: bool,
        expected_token: Optional[str],
        expected_header: Optional[dict[str, str]],
    ) -> None:
        """Test the `reset_connection` method."""

        # Mock the `_new_session` method
        with patch.object(
            Connection, "_new_session", new_callable=Mock
        ) as mock_new_session:
            # Create a Connection
            connection = Connection(
                hostname="localhost",
                username="user",
                password="pass",
            )

            # Set the initial state
            connection._connected = connected
            connection._token = token
            connection._header = header

            # Call `reset_connection`
            connection.reset_connection()

            # Verify the state after calling `reset_connection`
            assert connection._connected == expected_connected
            assert connection._token == expected_token
            assert connection._header == expected_header

            # Verify `_new_session` was called during initialization
            mock_new_session.assert_called_once()

    @pytest.mark.parametrize(
        "initial_connected, expected_connected",
        [
            # Case 1: Connection is active
            (True, True),
            # Case 2: Connection is inactive
            (False, False),
        ],
    )
    def test_connected_property(
        self, initial_connected: bool, expected_connected: bool
    ) -> None:
        """Test the `connected` property."""

        # Mock the `_new_session` method
        with patch.object(
            Connection, "_new_session", new_callable=Mock
        ) as mock_new_session:
            # Create a Connection
            connection = Connection(
                hostname="localhost",
                username="user",
                password="pass",
            )

            # Set the initial state of `_connected`
            connection._connected = initial_connected

            # Verify the `connected` property
            assert connection.connected == expected_connected

            # Verify `_new_session` was called during initialization
            mock_new_session.assert_called_once()
