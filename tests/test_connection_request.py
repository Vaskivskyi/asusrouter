"""Tests for the connection module / Part 3 / Requests."""

import asyncio
import ssl
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from asusrouter.config import ARConfigKey
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
        make_request: AsyncPatch,
        reset_connection: SyncPatch,
    ) -> None:
        """Test the `_send_request` method with parameterized scenarios."""

        # Create a Connection
        connection = connection_factory()

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
        ("debug_payload", "endpoint", "payload", "expected_log"),
        [
            (True, EndpointService.LOGIN, "secret", None),
            (True, EndpointService.LOGOUT, "logout_payload", "logout_payload"),
            (False, EndpointService.LOGIN, "secret", None),
            (False, EndpointService.LOGOUT, "logout_payload", None),
        ],
        ids=[
            "debug_login_redacted",
            "debug_other_payload",
            "no_debug_login",
            "no_debug_other",
        ],
    )
    async def test_send_request_logging_payload(
        self,
        debug_payload: bool,
        endpoint: EndpointService,
        payload: str,
        expected_log: str | None,
        connection_factory: ConnectionFactory,
        make_request: AsyncPatch,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that payload logging in _send_request respects config."""

        connection = connection_factory()
        make_request(connection, return_value=(200, {}, "{}"))

        # Patch ARConfig.get to return debug_payload
        monkeypatch.setattr(
            "asusrouter.connection.ARConfig.get",
            lambda key: debug_payload
            if key == ARConfigKey.DEBUG_PAYLOAD
            else None,
        )

        # Patch logger
        with patch("asusrouter.connection._LOGGER.debug") as mock_debug:
            await connection._send_request(endpoint, payload=payload)

            if expected_log is not None:
                mock_debug.assert_any_call(
                    "Sending request to %s with payload: %s",
                    endpoint,
                    expected_log,
                )
            else:
                mock_debug.assert_any_call("Sending request to %s", endpoint)
                # Should not log payload
                for call in mock_debug.call_args_list:
                    assert payload not in call.args

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
        make_request: AsyncPatch,
    ) -> None:
        """Test that fallback tracker is reset on successful requests."""

        config = {ARCCKey.ALLOW_MULTIPLE_FALLBACKS: allow_multiple_fallbacks}
        connection = connection_factory(config=config)
        make_request(connection, return_value=MOCK_REQUEST_RESULT)

        # Replace _used_fallbacks with a Mock to track clear calls
        mock_fallbacks = Mock()
        connection._used_fallbacks = mock_fallbacks

        await connection._send_request(EndpointService.LOGIN)

        if expected_clear_called:
            mock_fallbacks.clear.assert_called_once()
        else:
            mock_fallbacks.clear.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_request_ssl_error_non_strict(
        self,
        connection_factory: ConnectionFactory,
        make_request: AsyncPatch,
    ) -> None:
        """Test the `_send_request` method with SSL verification errors."""

        connection = connection_factory()

        def make_request_side_effect(*args: Any, **kwargs: Any) -> Any:
            """Simulate the behavior of the _make_request method."""

            # First call: raise SSL error, subsequent calls: return success
            if not getattr(make_request_side_effect, "_called", False):
                setattr(make_request_side_effect, "_called", True)
                raise ssl.SSLCertVerificationError
            return MOCK_REQUEST_RESULT

        make_request(connection, side_effect=make_request_side_effect)

        with patch.object(
            connection, "_fallback", new_callable=AsyncMock
        ) as mock_fallback:
            result = await connection._send_request(EndpointService.LOGIN)
            mock_fallback.assert_called_once()
            assert result == MOCK_REQUEST_RESULT

    @pytest.mark.asyncio
    async def test_send_request_ssl_error_strict(
        self,
        connection_factory: ConnectionFactory,
        make_request: AsyncPatch,
    ) -> None:
        """Test the `_send_request` method with SSL verification errors."""

        connection = connection_factory(config={ARCCKey.STRICT_SSL: True})
        make_request(connection, side_effect=ssl.SSLCertVerificationError)

        with pytest.raises(AsusRouterSSLCertificateError):
            await connection._send_request(EndpointService.LOGIN)

    @pytest.mark.asyncio
    async def test_send_request_fail_fallback_not_allowed(
        self,
        connection_factory: ConnectionFactory,
        make_request: AsyncPatch,
        reset_connection: SyncPatch,
    ) -> None:
        """Test the `_send_request` method when fallback is not allowed."""

        connection = connection_factory(config={ARCCKey.ALLOW_FALLBACK: False})
        make_request(
            connection,
            side_effect=aiohttp.ClientConnectorError(Mock(), Mock()),
        )

        mock_reset_connection = reset_connection(connection)

        with pytest.raises(AsusRouterConnectionError):
            await connection._send_request(EndpointService.LOGIN)
        mock_reset_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_request_ssl_error_fallback(
        self,
        connection_factory: ConnectionFactory,
        make_request: AsyncPatch,
    ) -> None:
        """Test the `_send_request` method with fallback."""

        connection = connection_factory(config={ARCCKey.ALLOW_FALLBACK: True})
        make_request(
            connection,
            side_effect=aiohttp.ClientConnectorError(Mock(), Mock()),
        )

        with patch.object(
            connection, "_async_handle_fallback", new_callable=AsyncMock
        ) as mock_handle_fallback:
            # Simulate fallback returns dummy response
            mock_handle_fallback.return_value = MOCK_REQUEST_RESULT

            await connection._send_request(EndpointService.LOGIN)

            mock_handle_fallback.assert_called_once_with(
                callback=connection._send_request,
                endpoint=EndpointService.LOGIN,
                payload=None,
                headers=None,
                request_type=RequestType.POST,
            )

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
