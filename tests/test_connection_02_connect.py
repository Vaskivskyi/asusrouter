"""Tests for the connection module / Part 2 / Connect & Disconnect."""

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from asusrouter.connection import Connection
from asusrouter.const import USER_AGENT
from asusrouter.error import (
    AsusRouterAccessError,
    AsusRouterError,
    AsusRouterLogoutError,
    AsusRouterSSLCertificateError,
)
from asusrouter.modules.endpoint import EndpointService
from tests.helpers import AsyncPatch, ConnectionFactory, SyncPatch


class TestConnectionConnect:
    """Tests for the Connection class connect and disconnect."""

    @pytest.mark.asyncio
    async def test_new_session(
        self, connection_factory: ConnectionFactory
    ) -> None:
        """Test the `_new_session` method."""

        # Create a Connection
        connection = connection_factory(timeout=30)

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
            # with no arguments
            mock_tcp_connector.assert_called_once()

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
    @pytest.mark.parametrize(
        ("closed", "manage_session", "expected_awaited"),
        [
            (False, True, True),  # Case 1: Session is not closed
            (True, True, False),  # Case 2: Session is already closed
            (False, False, False),  # Case 3: _manage_session is False
        ],
        ids=["not_closed", "already_closed", "manage_session_false"],
    )
    async def test_async_close(
        self,
        closed: bool,
        manage_session: bool,
        expected_awaited: bool,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Parametrized test for the `async_close` method."""

        connection = connection_factory()
        mock_session = AsyncMock()
        connection._session = mock_session
        connection._manage_session = manage_session
        mock_session.closed = closed

        await connection.async_close()

        if expected_awaited:
            mock_session.close.assert_awaited_once()
        else:
            mock_session.close.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_async_connect(
        self,
        connection_factory: ConnectionFactory,
        async_connect_with_lock: AsyncPatch,
    ) -> None:
        """Test the `async_connect` method."""

        # Create a Connection
        connection = connection_factory(timeout=30)

        # Mock _async_connect_with_lock
        mock_async_connect_with_lock = async_connect_with_lock(connection)

        # Case 1: Connection succeeds
        mock_async_connect_with_lock.return_value = True
        result = await connection.async_connect()
        mock_async_connect_with_lock.assert_awaited_once_with(None)
        assert result is True

        # Case 2: Connection times out
        mock_async_connect_with_lock.reset_mock()
        mock_async_connect_with_lock.side_effect = asyncio.TimeoutError
        result = await connection.async_connect()
        mock_async_connect_with_lock.assert_awaited_once_with(None)
        assert result is False

    @pytest.mark.asyncio
    async def test_async_connect_reuses_inflight_task(
        self,
        connection_factory: ConnectionFactory,
        async_connect_with_lock: AsyncPatch,
    ) -> None:
        """Ensure async_connect reuses an existing in-flight connect task."""

        connection = connection_factory(timeout=30)

        # Patch the underlying method so we can assert it was NOT called.
        mock_async_connect_with_lock = async_connect_with_lock(connection)

        # Create a dummy in-flight task that completes immediately.
        async def dummy_connect() -> bool:
            return True

        connection._connect_task = asyncio.create_task(dummy_connect())

        # Call async_connect — it should await the existing task and NOT call
        # _async_connect_with_lock again.
        result = await connection.async_connect()
        assert result is True
        mock_async_connect_with_lock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_async_connect_cancelled_handling(
        self,
        connection_factory: ConnectionFactory,
        async_connect_with_lock: AsyncPatch,
    ) -> None:
        """When the underlying connect is cancelled.

        async_connect should return False.
        """

        connection = connection_factory(timeout=30)

        mock_async_connect_with_lock = async_connect_with_lock(connection)
        mock_async_connect_with_lock.side_effect = asyncio.CancelledError()

        result = await connection.async_connect()
        assert result is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        (
            "connected",
            "send_request_result",
            "send_request_side_effect",
            "expected_result",
            "expected_exception",
            "exception_message",
        ),
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
        ids=[
            "already_connected",
            "successful_connection",
            "access_error",
            "unexpected_error",
            "generic_asusrouter_error",
            "no_token_received",
        ],
    )
    async def test_async_connect_with_lock(
        self,
        connected: bool,
        send_request_result: tuple[int, Any, str] | None,
        send_request_side_effect: Exception | None,
        expected_result: bool | None,
        expected_exception: type[BaseException] | None,
        exception_message: str | None,
        connection_factory: ConnectionFactory,
        send_request: AsyncPatch,
    ) -> None:
        """Test `_async_connect_with_lock` with parameterized scenarios."""

        # Create a Connection
        connection = connection_factory()

        # Set the initial connection state
        connection._connected = connected

        mock_send_request = send_request(connection)
        # Configure the mock based on the test case
        if send_request_side_effect:
            mock_send_request.side_effect = send_request_side_effect
        else:
            mock_send_request.return_value = send_request_result

        if expected_exception:
            # Verify that the expected exception is raised
            with pytest.raises(expected_exception, match=exception_message):
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
        if not connected and not expected_exception and send_request_result:
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
        (
            "connected",
            "send_request_side_effect",
            "expected_result",
            "reset_connection_called",
        ),
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
        send_request_side_effect: Exception | None,
        expected_result: bool,
        reset_connection_called: bool,
        connection_factory: ConnectionFactory,
        reset_connection: SyncPatch,
        send_request: AsyncPatch,
    ) -> None:
        """Test the `async_disconnect` method with parameterized scenarios."""

        # Create a Connection
        connection = connection_factory()

        # Set the initial connection state
        connection._connected = connected

        # Mock the `_send_request` and `reset_connection` methods
        mock_send_request = send_request(connection)
        mock_reset_connection = reset_connection(connection)

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
            mock_send_request.assert_called_once_with(EndpointService.LOGOUT)
        else:
            mock_send_request.assert_not_called()

        # Verify `reset_connection` was called if expected
        if reset_connection_called:
            mock_reset_connection.assert_called_once()
        else:
            mock_reset_connection.assert_not_called()

    @pytest.mark.parametrize(
        (
            "connected",
            "token",
            "header",
            "expected_connected",
            "expected_token",
            "expected_header",
        ),
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
        token: str | None,
        header: dict[str, str] | None,
        expected_connected: bool,
        expected_token: str | None,
        expected_header: dict[str, str] | None,
        connection_factory: ConnectionFactory,
        new_session: SyncPatch,
    ) -> None:
        """Test the `reset_connection` method."""

        # Mock the `_new_session` method
        mock_new_session = new_session(Connection)

        # Create a Connection
        connection = connection_factory()

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
        ("initial_connected", "expected_connected"),
        [
            # Case 1: Connection is active
            (True, True),
            # Case 2: Connection is inactive
            (False, False),
        ],
    )
    def test_connected_property(
        self,
        initial_connected: bool,
        expected_connected: bool,
        connection_factory: ConnectionFactory,
        new_session: SyncPatch,
    ) -> None:
        """Test the `connected` property."""

        # Mock the `_new_session` method
        mock_new_session = new_session(Connection)

        # Create a Connection
        connection = connection_factory()

        # Set the initial state of `_connected`
        connection._connected = initial_connected

        # Verify the `connected` property
        assert connection.connected == expected_connected

        # Verify `_new_session` was called during initialization
        mock_new_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_connect_returns_immediately_if_already_connected(
        self,
        connection_factory: ConnectionFactory,
        async_connect_with_lock: AsyncPatch,
    ) -> None:
        """async_connect should return immediately if already connected."""
        connection = connection_factory()
        connection._connected = True

        mock_async = async_connect_with_lock(connection)

        result = await connection.async_connect()
        assert result is True
        mock_async.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_async_connect_with_lock_translates_ssl_error(
        self,
        connection_factory: ConnectionFactory,
        send_request: AsyncPatch,
    ) -> None:
        """If _send_request raises SSLCertVerificationError.

        async_connect should raise AsusRouterAccessError.
        """
        connection = connection_factory()
        mock_send = send_request(connection)
        mock_send.side_effect = AsusRouterSSLCertificateError("bad cert")

        with pytest.raises(
            AsusRouterAccessError, match="due to the SSL certificate error"
        ):
            await connection._async_connect_with_lock()

    @pytest.mark.asyncio
    async def test_async_connect_with_lock_respects_race(
        self,
        connection_factory: ConnectionFactory,
        send_request: AsyncPatch,
    ) -> None:
        """If another task connected while network IO ran.

        _async_connect_with_lock should not overwrite state.
        """
        connection = connection_factory()

        async def send_request_side(
            *a: Any, **kw: Any
        ) -> tuple[int, dict[str, str], str]:
            # simulate another task completing the connection
            # while we performed network IO
            connection._connected = True
            connection._token = "existing-token"
            return (200, {}, json.dumps({"asus_token": "new-token"}))

        mock_send = send_request(connection)
        mock_send.side_effect = send_request_side

        result = await connection._async_connect_with_lock()
        assert result is True
        # token must remain the one set by the racing task, not overwritten
        assert connection._token == "existing-token"
