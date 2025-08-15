"""Tests for the connection module / Part 5 / Make Request."""

from unittest.mock import AsyncMock, MagicMock
from urllib.parse import quote

import pytest

from asusrouter.connection_config import ARConnectionConfigKey as ARCCKey
from asusrouter.const import DEFAULT_PORT_HTTP, RequestType
from asusrouter.modules.endpoint import EndpointService
from tests.helpers import AsyncPatch, ConnectionFactory


class TestConnectionMakeRequest:
    """Tests for the Connection _make_request method."""

    TEST_HOSTNAME = "router"
    TEST_PORT = DEFAULT_PORT_HTTP
    DEFAULT_HEADERS = {"default": "header"}
    CUSTOM_HEADERS = {"custom": "header"}

    def _create_mock_context_manager(
        self, mock_response: MagicMock
    ) -> AsyncMock:
        """Create a proper async context manager mock."""

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response
        mock_cm.__aexit__.return_value = None
        return mock_cm

    def _create_mock_response(
        self, status: int, headers: dict[str, str], text: str
    ) -> MagicMock:
        """Create a mock response."""

        mock_response = MagicMock()
        mock_response.status = status
        mock_response.headers = headers
        mock_response.text = AsyncMock(return_value=text)
        return mock_response

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        (
            "request_type",
            "payload",
            "expected_url_suffix",
            "expected_data",
            "response_text",
            "response_headers",
            "response_status",
            "expect_retry",
        ),
        [
            # Session closed, should retry after reconnect
            (
                RequestType.POST,
                "data",
                f"/{EndpointService.LOGIN.value}",
                quote("data"),
                "ok",
                {"h": "v"},
                200,
                True,
            ),
            # Session open, POST request
            (
                RequestType.POST,
                "data",
                f"/{EndpointService.LOGIN.value}",
                quote("data"),
                "ok",
                {"h": "v"},
                200,
                False,
            ),
            # Session open, GET request with payload
            # (test `;` → `&` replacement)
            (
                RequestType.GET,
                "param1=val1;param2=val2",
                f"/{EndpointService.LOGIN.value}?param1=val1&param2=val2",
                None,
                "ok",
                {"h": "v"},
                200,
                False,
            ),
            # Session open, GET request without payload
            (
                RequestType.GET,
                None,
                f"/{EndpointService.LOGIN.value}",
                None,
                "ok",
                {"h": "v"},
                200,
                False,
            ),
        ],
        ids=[
            "session_closed_retry",
            "post_request",
            "get_request_with_payload",
            "get_request_no_payload",
        ],
    )
    async def test_make_request(
        self,
        request_type: RequestType,
        payload: str | None,
        expected_url_suffix: str,
        expected_data: str | None,
        response_text: str,
        response_headers: dict[str, str],
        response_status: int,
        expect_retry: bool,
        connection_factory: ConnectionFactory,
        async_connect: AsyncPatch,
        new_session: AsyncPatch,
    ) -> None:
        """Test _make_request for basic flows and session recreation."""

        connection = connection_factory()
        # Set connection properties for URL building
        connection._hostname = self.TEST_HOSTNAME
        connection.config.set(ARCCKey.PORT, self.TEST_PORT)
        connection.config.set(ARCCKey.USE_SSL, False)
        connection._header = self.DEFAULT_HEADERS

        # Prepare response and context manager
        mock_response = self._create_mock_response(
            response_status, response_headers, response_text
        )
        mock_cm = self._create_mock_context_manager(mock_response)

        if expect_retry:
            # First session is closed, second is open
            mock_session_closed = MagicMock()
            mock_session_closed.closed = True

            mock_session_open = MagicMock()
            mock_session_open.closed = False
            mock_session_open.request = MagicMock(return_value=mock_cm)

            connection._session = mock_session_closed

            # Patch _new_session to return open session on retry
            mock_new_session = new_session(
                connection, return_value=mock_session_open
            )
            mock_async_connect = async_connect(connection)
        else:
            mock_session = MagicMock()
            mock_session.closed = False
            mock_session.request = MagicMock(return_value=mock_cm)
            connection._session = mock_session

            mock_new_session = new_session(connection)
            mock_async_connect = async_connect(connection)

        # Patch _dumpback
        connection._dumpback = AsyncMock()

        result = await connection._make_request(
            EndpointService.LOGIN,
            payload=payload,
            headers=None,
            request_type=request_type,
        )

        # Verify retry behavior
        if expect_retry:
            mock_new_session.assert_called_once()
            mock_async_connect.assert_awaited_once()
            active_session = mock_session_open
        else:
            mock_new_session.assert_not_called()
            mock_async_connect.assert_not_awaited()
            active_session = mock_session

        # Verify request was called with correct parameters
        expected_url = (
            f"http://{self.TEST_HOSTNAME}:"
            f"{self.TEST_PORT}{expected_url_suffix}"
        )
        active_session.request.assert_called_once_with(
            request_type.value,
            expected_url,
            data=expected_data,
            headers=self.DEFAULT_HEADERS,
            ssl=connection.config.get(ARCCKey.VERIFY_SSL),
        )

        # Check result
        assert result == (response_status, response_headers, response_text)

        # Check dumpback called
        connection._dumpback.assert_awaited_once_with(
            EndpointService.LOGIN,
            payload,
            response_status,
            response_headers,
            response_text,
        )

    @pytest.mark.asyncio
    async def test_make_request_no_session(
        self,
        connection_factory: ConnectionFactory,
        async_connect: AsyncPatch,
        new_session: AsyncPatch,
    ) -> None:
        """Test _make_request when session is None."""

        connection = connection_factory()
        connection._session = None  # type: ignore[assignment]

        mock_session_open = MagicMock()
        mock_session_open.closed = False

        mock_response = self._create_mock_response(200, {"h": "v"}, "ok")
        mock_cm = self._create_mock_context_manager(mock_response)
        mock_session_open.request = MagicMock(return_value=mock_cm)

        mock_new_session = new_session(
            connection, return_value=mock_session_open
        )
        mock_async_connect = async_connect(connection)
        connection._dumpback = AsyncMock()

        result = await connection._make_request(EndpointService.LOGIN)

        mock_new_session.assert_called_once()
        mock_async_connect.assert_awaited_once()
        assert result == (200, {"h": "v"}, "ok")

    @pytest.mark.asyncio
    async def test_make_request_unicode_decode_error(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Test _make_request handles UnicodeDecodeError."""

        connection = connection_factory()
        mock_session = MagicMock()
        mock_session.closed = False
        connection._session = mock_session

        # Patch response to raise UnicodeDecodeError then succeed
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"h": "v"}
        mock_response.text = AsyncMock(
            side_effect=[
                UnicodeDecodeError("utf-8", b"", 0, 1, "bad"),
                "fixed",
            ]
        )

        mock_cm = self._create_mock_context_manager(mock_response)
        mock_session.request = MagicMock(return_value=mock_cm)
        connection._dumpback = AsyncMock()

        result = await connection._make_request(
            EndpointService.LOGIN,
            payload="data",
            headers=None,
            request_type=RequestType.POST,
        )

        assert result == (200, {"h": "v"}, "fixed")
        connection._dumpback.assert_awaited_once_with(
            EndpointService.LOGIN, "data", 200, {"h": "v"}, "fixed"
        )

    @pytest.mark.asyncio
    async def test_make_request_custom_headers(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Test _make_request uses custom headers when provided."""

        connection = connection_factory()
        mock_session = MagicMock()
        mock_session.closed = False
        connection._session = mock_session

        connection._header = self.DEFAULT_HEADERS
        custom_headers = self.CUSTOM_HEADERS

        mock_response = self._create_mock_response(200, {"h": "v"}, "ok")
        mock_cm = self._create_mock_context_manager(mock_response)
        mock_session.request = MagicMock(return_value=mock_cm)
        connection._dumpback = AsyncMock()

        await connection._make_request(
            EndpointService.LOGIN,
            payload=None,
            headers=custom_headers,
            request_type=RequestType.POST,
        )

        # Should use custom headers, not default
        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        assert call_args.kwargs["headers"] == custom_headers

    @pytest.mark.asyncio
    async def test_make_request_no_dumpback(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Test _make_request works when no dumpback is set."""

        connection = connection_factory()
        mock_session = MagicMock()
        mock_session.closed = False
        connection._session = mock_session
        connection._dumpback = None  # No dumpback

        mock_response = self._create_mock_response(200, {"h": "v"}, "ok")
        mock_cm = self._create_mock_context_manager(mock_response)
        mock_session.request = MagicMock(return_value=mock_cm)

        result = await connection._make_request(
            EndpointService.LOGIN,
            payload=None,
            headers=None,
            request_type=RequestType.POST,
        )

        assert result == (200, {"h": "v"}, "ok")
        # Should not raise any errors when dumpback is None
