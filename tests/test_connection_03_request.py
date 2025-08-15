"""Tests for the connection module / Part 3 / Requests."""

import asyncio
import ssl
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from asusrouter.connection_config import ARConnectionConfigKey as ARCCKey
from asusrouter.const import RequestType
from asusrouter.error import (
    AsusRouter404Error,
    AsusRouterAccessError,
    AsusRouterConnectionError,
    AsusRouterSSLCertificateError,
    AsusRouterTimeoutError,
)
from asusrouter.modules.endpoint import EndpointService
from tests.helpers import AsyncPatch, ConnectionFactory, SyncPatch

SEND_REQUEST_CASES = [
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
        TimeoutError("operation timed out"),
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
]
SEND_REQUEST_IDS = [
    "success",
    "404_error",
    "non_200",
    "access_error",
    "client_connector_error",
    "client_connection_error",
    "client_os_error",
    "unexpected_error",
    "timeout_error",
    "cancelled_error",
]

MOCK_REQUEST_RESULT = (200, {"header": "value"}, '{"key": "value"}')


class TestConnectionRequests:
    """Tests for the Connection class requests."""

    DEFAULT_ENDPOINT = EndpointService.LOGIN

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        (
            "resp_status",
            "resp_headers",
            "resp_content",
            "make_request_side_effect",
            "expected_exception",
            "exception_message",
        ),
        SEND_REQUEST_CASES,
        ids=SEND_REQUEST_IDS,
    )
    async def test_send_request(
        self,
        resp_status: int | None,
        resp_headers: dict[str, str] | None,
        resp_content: str | None,
        make_request_side_effect: Exception | None,
        expected_exception: type[BaseException] | None,
        exception_message: str | None,
        connection_factory: ConnectionFactory,
        log_request: SyncPatch,
        make_request: AsyncPatch,
        reset_connection: SyncPatch,
    ) -> None:
        """Test the `_send_request` method with parameterized scenarios."""

        # Create a Connection
        connection = connection_factory()

        mock_log_request = log_request(connection)
        mock_reset_connection = reset_connection(connection)
        with patch(
            "asusrouter.connection.handle_access_error"
        ) as mock_handle_access_error:
            # Configure the mock for _make_request
            if make_request_side_effect:
                # mock_make_request.side_effect = make_request_side_effect
                mock_make_request = make_request(
                    connection, side_effect=make_request_side_effect
                )
            else:
                mock_make_request = make_request(
                    connection,
                    return_value=(
                        resp_status,
                        resp_headers,
                        resp_content,
                    ),
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
                    await connection._send_request(self.DEFAULT_ENDPOINT)
            else:
                result = await connection._send_request(self.DEFAULT_ENDPOINT)
                assert result == (resp_status, resp_headers, resp_content)

            # Verify _make_request was called with expected parameters
            mock_make_request.assert_called_once_with(
                self.DEFAULT_ENDPOINT, None, None, RequestType.POST
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

            # Check that logging was called with the expected payload
            mock_log_request.assert_called_once_with(
                self.DEFAULT_ENDPOINT, None
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("allow_multiple_fallbacks", "expected_clear_called"),
        [
            (True, True),
            (False, False),
        ],
        ids=["multiple_fallbacks_enabled", "multiple_fallbacks_disabled"],
    )
    async def test_send_request_resets_fallback_tracker(
        self,
        allow_multiple_fallbacks: bool,
        expected_clear_called: bool,
        connection_factory: ConnectionFactory,
        log_request: SyncPatch,
        make_request: AsyncPatch,
    ) -> None:
        """Test that fallback tracker is reset on successful requests."""

        config = {ARCCKey.ALLOW_MULTIPLE_FALLBACKS: allow_multiple_fallbacks}
        connection = connection_factory(config=config)
        mock_log_request = log_request(connection)
        make_request(connection, return_value=MOCK_REQUEST_RESULT)

        # Replace _used_fallbacks with a Mock to track clear calls
        mock_fallbacks = Mock()
        connection._used_fallbacks = mock_fallbacks

        await connection._send_request(self.DEFAULT_ENDPOINT)

        if expected_clear_called:
            mock_fallbacks.clear.assert_called_once()
        else:
            mock_fallbacks.clear.assert_not_called()

        # Check that logging was called with the expected payload
        mock_log_request.assert_called_once_with(self.DEFAULT_ENDPOINT, None)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("allow_fallback"),
        [
            True,
            False,
        ],
        ids=["fallback_allowed", "fallback_not_allowed"],
    )
    async def test_send_request_ssl_error_non_strict(
        self,
        allow_fallback: bool,
        connection_factory: ConnectionFactory,
        fallback: AsyncPatch,
        log_request: SyncPatch,
        make_request: AsyncPatch,
    ) -> None:
        """Test the `_send_request` method with SSL verification errors."""

        connection = connection_factory(
            config={ARCCKey.ALLOW_FALLBACK: allow_fallback}
        )
        mock_log_request = log_request(connection)

        def make_request_side_effect(*args: Any, **kwargs: Any) -> Any:
            """Simulate the behavior of the _make_request method."""

            # First call: raise SSL error, subsequent calls: return success
            if not getattr(make_request_side_effect, "_called", False):
                setattr(make_request_side_effect, "_called", True)
                raise ssl.SSLCertVerificationError
            return MOCK_REQUEST_RESULT

        mock_fallback = fallback(connection)
        make_request(connection, side_effect=make_request_side_effect)
        if allow_fallback:
            # should fallback and succeed
            result = await connection._send_request(self.DEFAULT_ENDPOINT)
            mock_fallback.assert_called_once()
            assert result == MOCK_REQUEST_RESULT
            # Check log calls
            assert mock_log_request.call_count == 2  # noqa: PLR2004
            mock_log_request.assert_called_with(self.DEFAULT_ENDPOINT, None)
        else:
            # no fallback allowed -> should raise SSL certificate error
            with pytest.raises(AsusRouterSSLCertificateError):
                await connection._send_request(self.DEFAULT_ENDPOINT)
            mock_fallback.assert_not_called()
            # Check log calls
            mock_log_request.assert_called_once_with(
                self.DEFAULT_ENDPOINT, None
            )

    @pytest.mark.asyncio
    async def test_send_request_ssl_error_strict(
        self,
        connection_factory: ConnectionFactory,
        log_request: SyncPatch,
        make_request: AsyncPatch,
    ) -> None:
        """Test the `_send_request` method with SSL verification errors."""

        connection = connection_factory(config={ARCCKey.STRICT_SSL: True})
        mock_log_request = log_request(connection)
        make_request(connection, side_effect=ssl.SSLCertVerificationError)

        with pytest.raises(AsusRouterSSLCertificateError):
            await connection._send_request(self.DEFAULT_ENDPOINT)

        # Check that logging was called with the expected payload
        mock_log_request.assert_called_once_with(self.DEFAULT_ENDPOINT, None)

    @pytest.mark.asyncio
    async def test_send_request_fail_fallback_not_allowed(
        self,
        connection_factory: ConnectionFactory,
        log_request: SyncPatch,
        make_request: AsyncPatch,
        reset_connection: SyncPatch,
    ) -> None:
        """Test the `_send_request` method when fallback is not allowed."""

        connection = connection_factory(config={ARCCKey.ALLOW_FALLBACK: False})
        mock_log_request = log_request(connection)
        make_request(
            connection,
            side_effect=aiohttp.ClientConnectorError(Mock(), Mock()),
        )

        mock_reset_connection = reset_connection(connection)

        with pytest.raises(AsusRouterConnectionError):
            await connection._send_request(self.DEFAULT_ENDPOINT)
        mock_reset_connection.assert_called_once()

        # Check that logging was called with the expected payload
        mock_log_request.assert_called_once_with(self.DEFAULT_ENDPOINT, None)

    @pytest.mark.asyncio
    async def test_send_request_ssl_error_fallback(
        self,
        connection_factory: ConnectionFactory,
        log_request: SyncPatch,
        make_request: AsyncPatch,
    ) -> None:
        """Test the `_send_request` method with fallback."""

        connection = connection_factory(config={ARCCKey.ALLOW_FALLBACK: True})
        mock_log_request = log_request(connection)
        make_request(
            connection,
            side_effect=aiohttp.ClientConnectorError(Mock(), Mock()),
        )

        with patch.object(
            connection, "_async_handle_fallback", new_callable=AsyncMock
        ) as mock_handle_fallback:
            # Simulate fallback returns dummy response
            mock_handle_fallback.return_value = MOCK_REQUEST_RESULT

            await connection._send_request(self.DEFAULT_ENDPOINT)

            mock_handle_fallback.assert_called_once_with(
                callback=connection._send_request,
                endpoint=self.DEFAULT_ENDPOINT,
                payload=None,
                headers=None,
                request_type=RequestType.POST,
            )

        # Check that logging was called with the expected payload
        mock_log_request.assert_called_once_with(self.DEFAULT_ENDPOINT, None)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        (
            "connected",
            "connect_result",
            "send_request_result",
            "send_request_side_effect",
            "expected_exception",
            "exception_message",
        ),
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
        connect_result: bool | None,
        send_request_result: tuple[int, dict[str, str], str] | None,
        send_request_side_effect: Exception | None,
        expected_exception: type[BaseException] | None,
        exception_message: str | None,
        connection_factory: ConnectionFactory,
        async_connect: AsyncPatch,
        send_request: AsyncPatch,
    ) -> None:
        """Test the `async_query` method with parameterized scenarios."""

        # Create a Connection
        connection = connection_factory()

        # Set the initial connection state
        connection._connected = connected

        # Mock the `async_connect` and `_send_request` methods
        mock_async_connect = async_connect(connection)
        mock_send_request = send_request(connection)

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
            with pytest.raises(expected_exception, match=exception_message):
                await connection.async_query(self.DEFAULT_ENDPOINT)
        else:
            # Call `async_query`
            result = await connection.async_query(self.DEFAULT_ENDPOINT)

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
                self.DEFAULT_ENDPOINT, None, None, RequestType.POST
            )
        else:
            mock_send_request.assert_not_called()
