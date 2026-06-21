"""Tests for connection module — request handling."""

from __future__ import annotations

import asyncio
import ssl
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from urllib.parse import quote

import aiohttp
import pytest

from asusrouter.connection_config import ARConnectionConfigKey as ARCCKey
from asusrouter.const import DEFAULT_PORT_HTTP, RequestType
from asusrouter.error import (
    AsusRouter404Error,
    AsusRouterAccessError,
    AsusRouterConnectionError,
    AsusRouterError,
    AsusRouterSSLCertificateError,
    AsusRouterTimeoutError,
)
from asusrouter.modules.endpoint_v2 import AREndpoint
from tests.helpers import AsyncPatch, ConnectionFactory, SyncPatch


class TestEnsureSession:
    """Tests for Connection._ensure_session."""

    async def test_session_none_creates_session(
        self,
        connection_factory: ConnectionFactory,
        async_connect: AsyncPatch,
        new_session: SyncPatch,
    ) -> None:
        """Creates session when _session is None; does not reconnect."""

        conn = connection_factory()
        conn._session = None
        mock_new_session = new_session(conn)
        mock_connect = async_connect(conn)

        await conn._ensure_session()

        mock_new_session.assert_called_once()
        mock_connect.assert_not_called()
        assert conn._session is mock_new_session.return_value

    async def test_session_open_no_action(
        self,
        connection_factory: ConnectionFactory,
        async_connect: AsyncPatch,
        new_session: SyncPatch,
    ) -> None:
        """Does nothing when session is already open."""

        conn = connection_factory()
        open_session = MagicMock()
        open_session.closed = False
        conn._session = open_session
        mock_new_session = new_session(conn)
        mock_connect = async_connect(conn)

        await conn._ensure_session()

        mock_new_session.assert_not_called()
        mock_connect.assert_not_called()
        assert conn._session is open_session

    async def test_session_closed_resets_and_reconnects(
        self,
        connection_factory: ConnectionFactory,
        new_session: SyncPatch,
    ) -> None:
        """Resets auth, creates new session, reconnects on closed session."""

        conn = connection_factory()
        conn._connected = True
        conn._token = "old"
        closed_session = MagicMock()
        closed_session.closed = True
        conn._session = closed_session
        mock_new_session = new_session(conn)

        async def set_connected() -> bool:
            conn._connected = True
            return True

        with patch.object(conn, "async_connect", side_effect=set_connected):
            await conn._ensure_session()

        assert conn._connected is True
        mock_new_session.assert_called_once()
        assert conn._session is mock_new_session.return_value

    async def test_session_closed_reconnect_fails_raises(
        self,
        connection_factory: ConnectionFactory,
        new_session: SyncPatch,
        async_connect: AsyncPatch,
    ) -> None:
        """Raises AsusRouterTimeoutError when reconnect fails."""

        conn = connection_factory()
        conn._connected = False
        closed_session = MagicMock()
        closed_session.closed = True
        conn._session = closed_session
        new_session(conn)
        async_connect(conn, return_value=False)  # does not set _connected

        with pytest.raises(
            AsusRouterTimeoutError, match="could not reconnect"
        ):
            await conn._ensure_session()

    async def test_session_closed_in_login_context_skips_reconnect(
        self,
        connection_factory: ConnectionFactory,
        new_session: SyncPatch,
        async_connect: AsyncPatch,
    ) -> None:
        """Recreates session but skips reconnect when in login task."""

        conn = connection_factory()
        closed_session = MagicMock()
        closed_session.closed = True
        conn._session = closed_session
        mock_new_session = new_session(conn)
        mock_connect = async_connect(conn)

        async def login_body() -> None:
            conn._connect_task = asyncio.current_task()
            await conn._ensure_session()

        await asyncio.create_task(login_body())

        mock_new_session.assert_called_once()
        mock_connect.assert_not_called()
        assert conn._session is mock_new_session.return_value


class TestAsyncQuery:
    """Tests for Connection.async_query."""

    @pytest.mark.parametrize(
        ("initial_connected", "connect_sets_connected", "expected_exc"),
        [
            (True, False, None),
            (False, True, None),
            (False, False, AsusRouterTimeoutError),
        ],
        ids=["already_connected", "connects_then_sends", "connect_fails"],
    )
    async def test_connection_guard(
        self,
        initial_connected: bool,
        connect_sets_connected: bool,
        expected_exc: type[BaseException] | None,
        connection_factory: ConnectionFactory,
        async_connect: AsyncPatch,
        send_request: AsyncPatch,
    ) -> None:
        """Connects if needed; raises on timeout; passes result on success."""

        conn = connection_factory()
        conn._connected = initial_connected

        async def connect_side_effect() -> bool:
            if connect_sets_connected:
                conn._connected = True
            return connect_sets_connected

        mock_connect = async_connect(conn, side_effect=connect_side_effect)
        mock_send = send_request(conn, return_value=(200, {}, "ok"))

        if expected_exc:
            with pytest.raises(expected_exc, match="initial connection"):
                await conn.async_query(AREndpoint.LOGIN)
            mock_send.assert_not_called()
        else:
            result = await conn.async_query(AREndpoint.LOGIN)
            assert result == (200, {}, "ok")
            mock_send.assert_called_once()

        if not initial_connected:
            mock_connect.assert_called_once()
        else:
            mock_connect.assert_not_called()

    async def test_passes_all_params_to_send_request(
        self,
        connection_factory: ConnectionFactory,
        send_request: AsyncPatch,
    ) -> None:
        """Passes all args through to _send_request unchanged."""

        conn = connection_factory()
        conn._connected = True
        mock_send = send_request(conn, return_value=(200, {}, "ok"))

        await conn.async_query(
            AREndpoint.LOGOUT,
            payload="body",
            headers={"x": "y"},
            request_type=RequestType.GET,
        )

        mock_send.assert_called_once_with(
            AREndpoint.LOGOUT, "body", {"x": "y"}, RequestType.GET
        )


class TestSendRequest:
    """Tests for Connection._send_request."""

    _ENDPOINT = AREndpoint.LOGIN

    def _open_session(self, conn: Any) -> None:
        """Give conn an open mock session so _ensure_session is a no-op."""

        mock = MagicMock()
        mock.closed = False
        conn._session = mock

    @pytest.mark.parametrize(
        ("make_return", "make_exc", "expected_exc"),
        [
            ((200, {}, "ok"), None, None),
            ((404, {}, ""), None, AsusRouter404Error),
            ((403, {}, ""), None, AsusRouterAccessError),
            (
                None,
                aiohttp.ClientConnectionError("err"),
                AsusRouterConnectionError,
            ),
            (None, aiohttp.ClientOSError("err"), AsusRouterConnectionError),
            (None, TimeoutError("t/o"), AsusRouterTimeoutError),
            (None, asyncio.CancelledError(), asyncio.CancelledError),
            (None, AsusRouterError("known"), AsusRouterError),
            (None, RuntimeError("boom"), RuntimeError),
        ],
        ids=[
            "success",
            "404",
            "non_200",
            "client_connection_error",
            "client_os_error",
            "timeout",
            "cancelled_propagates",
            "asusrouter_error_passthrough",
            "unexpected_raised",
        ],
    )
    async def test_response_and_exception_handling(
        self,
        make_return: tuple[int, dict, str] | None,
        make_exc: Exception | None,
        expected_exc: type[BaseException] | None,
        connection_factory: ConnectionFactory,
        make_request: AsyncPatch,
        log_request: SyncPatch,
    ) -> None:
        """Covers success, status-check errors, and exception propagation."""

        conn = connection_factory()
        self._open_session(conn)
        log_request(conn)

        if make_exc is not None:
            make_request(conn, side_effect=make_exc)
        else:
            make_request(conn, return_value=make_return)

        if expected_exc:
            with pytest.raises(expected_exc):
                await conn._send_request(self._ENDPOINT)
        else:
            result = await conn._send_request(self._ENDPOINT)
            assert result == make_return

    async def test_error_status_content_raises(
        self,
        connection_factory: ConnectionFactory,
        make_request: AsyncPatch,
        log_request: SyncPatch,
    ) -> None:
        """Calls handle_access_error and raises on error_status in body."""

        conn = connection_factory()
        self._open_session(conn)
        log_request(conn)
        content = '{"error_status": "8"}'
        make_request(conn, return_value=(200, {}, content))

        with patch("asusrouter.connection.handle_access_error") as mock_handle:
            mock_handle.side_effect = AsusRouterAccessError("blocked")
            with pytest.raises(AsusRouterAccessError):
                await conn._send_request(self._ENDPOINT)
            mock_handle.assert_called_once_with(
                self._ENDPOINT, 200, {}, content
            )

    @pytest.mark.parametrize(
        ("strict_ssl", "allow_fallback", "expected_exc"),
        [
            (True, True, AsusRouterSSLCertificateError),
            (False, False, AsusRouterSSLCertificateError),
            (False, True, None),
        ],
        ids=[
            "strict_blocks",
            "no_fallback_raises",
            "non_strict_with_fallback",
        ],
    )
    async def test_ssl_cert_verification_error(
        self,
        strict_ssl: bool,
        allow_fallback: bool,
        expected_exc: type[Exception] | None,
        connection_factory: ConnectionFactory,
        make_request: AsyncPatch,
        fallback: AsyncPatch,
        log_request: SyncPatch,
    ) -> None:
        """SSL cert error: strict and no-fallback raise; non-strict retries."""

        conn = connection_factory(
            config={
                ARCCKey.STRICT_SSL: strict_ssl,
                ARCCKey.ALLOW_FALLBACK: allow_fallback,
            }
        )
        self._open_session(conn)
        log_request(conn)
        mock_fallback = fallback(conn)

        call_count = 0

        async def ssl_then_ok(*_: Any) -> tuple[int, dict, str]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise aiohttp.ClientConnectorSSLError(
                    MagicMock(), ssl.SSLCertVerificationError()
                )
            return (200, {}, "ok")

        make_request(conn, side_effect=ssl_then_ok)

        if expected_exc:
            with pytest.raises(expected_exc):
                await conn._send_request(self._ENDPOINT)
            mock_fallback.assert_not_called()
        else:
            result = await conn._send_request(self._ENDPOINT)
            assert result == (200, {}, "ok")
            mock_fallback.assert_called_once()
            # Discovery complete: tracker cleared, config locked.
            assert not conn._used_fallbacks
            assert conn.config.get(ARCCKey.ALLOW_FALLBACK) is False

    @pytest.mark.parametrize(
        ("allow_fallback", "expected_exc"),
        [(True, None), (False, AsusRouterConnectionError)],
        ids=["fallback_dispatched", "no_fallback_raises"],
    )
    async def test_client_connector_error(
        self,
        allow_fallback: bool,
        expected_exc: type[Exception] | None,
        connection_factory: ConnectionFactory,
        make_request: AsyncPatch,
        reset_auth: SyncPatch,
        log_request: SyncPatch,
    ) -> None:
        """ClientConnectorError fallback path or raises and resets auth."""

        conn = connection_factory(
            config={ARCCKey.ALLOW_FALLBACK: allow_fallback}
        )
        self._open_session(conn)
        log_request(conn)
        make_request(
            conn,
            side_effect=aiohttp.ClientConnectorError(Mock(), Mock()),
        )
        mock_reset = reset_auth(conn)

        if allow_fallback:
            with patch.object(
                conn,
                "_handle_fallback",
                new_callable=AsyncMock,
                return_value=(200, {}, "ok"),
            ) as mock_fallback:
                result = await conn._send_request(self._ENDPOINT)

            assert result == (200, {}, "ok")
            mock_fallback.assert_called_once_with(
                callback=conn._send_request,
                endpoint=self._ENDPOINT,
                payload=None,
                headers=None,
                request_type=RequestType.POST,
            )
            mock_reset.assert_not_called()
        else:
            with pytest.raises(AsusRouterConnectionError):
                await conn._send_request(self._ENDPOINT)
            mock_reset.assert_called_once()

    @pytest.mark.parametrize(
        ("allow_multiple", "expect_lock"),
        [(True, False), (False, True)],
        ids=["multiple_clears_no_lock", "single_clears_and_locks"],
    )
    async def test_fallback_tracker_on_success(
        self,
        allow_multiple: bool,
        expect_lock: bool,
        connection_factory: ConnectionFactory,
        make_request: AsyncPatch,
        log_request: SyncPatch,
    ) -> None:
        """Always clears _used_fallbacks on success.

        Locks ALLOW_FALLBACK permanently when ALLOW_MULTIPLE_FALLBACKS is
        False.
        """

        conn = connection_factory(
            config={
                ARCCKey.ALLOW_FALLBACK: True,
                ARCCKey.ALLOW_MULTIPLE_FALLBACKS: allow_multiple,
            }
        )
        self._open_session(conn)
        log_request(conn)
        make_request(conn, return_value=(200, {}, "ok"))

        tracker = Mock()
        conn._used_fallbacks = tracker

        await conn._send_request(self._ENDPOINT)

        tracker.clear.assert_called_once()
        if expect_lock:
            assert conn.config.get(ARCCKey.ALLOW_FALLBACK) is False
        else:
            assert conn.config.get(ARCCKey.ALLOW_FALLBACK) is True

    async def test_log_request_called_with_correct_args(
        self,
        connection_factory: ConnectionFactory,
        make_request: AsyncPatch,
        log_request: SyncPatch,
    ) -> None:
        """_log_request is called before _make_request with correct args."""

        conn = connection_factory()
        self._open_session(conn)
        mock_log = log_request(conn)
        make_request(conn, return_value=(200, {}, "ok"))

        await conn._send_request(self._ENDPOINT, payload="p")

        mock_log.assert_called_once_with(self._ENDPOINT, "p")


class TestMakeRequest:
    """Tests for Connection._make_request."""

    _HOST = "router"
    _PORT = DEFAULT_PORT_HTTP
    _DEFAULT_HEADERS: dict[str, str] = {"default": "header"}

    def _setup_conn(self, conn: Any) -> MagicMock:
        """Configure conn for URL building and return the session mock."""

        conn._hostname = self._HOST
        conn.config.set(ARCCKey.PORT, self._PORT)
        conn.config.set(ARCCKey.USE_SSL, False)
        conn._header = self._DEFAULT_HEADERS
        conn._dumpback = None
        mock_session = MagicMock()
        mock_session.closed = False
        conn._session = mock_session
        return mock_session

    def _make_response_cm(
        self, status: int, headers: dict[str, str], text: str
    ) -> AsyncMock:
        """Create an async context manager mock for a response."""

        mock_response = MagicMock()
        mock_response.status = status
        mock_response.headers = headers
        mock_response.text = AsyncMock(return_value=text)
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response
        mock_cm.__aexit__.return_value = None
        return mock_cm

    @pytest.mark.parametrize(
        ("request_type", "payload", "expect_data", "url_suffix"),
        [
            (
                RequestType.POST,
                "data",
                quote("data"),
                f"/{AREndpoint.LOGIN.value}",
            ),
            (RequestType.POST, None, None, f"/{AREndpoint.LOGIN.value}"),
            (
                RequestType.GET,
                "a=1;b=2",
                None,
                f"/{AREndpoint.LOGIN.value}?a=1&b=2",
            ),
            (RequestType.GET, None, None, f"/{AREndpoint.LOGIN.value}"),
        ],
        ids=[
            "post_with_payload",
            "post_no_payload",
            "get_with_params",
            "get_no_params",
        ],
    )
    async def test_request_construction(
        self,
        request_type: RequestType,
        payload: str | None,
        expect_data: str | None,
        url_suffix: str,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Builds correct URL and data argument for each request type."""

        conn = connection_factory()
        mock_session = self._setup_conn(conn)
        mock_session.request = MagicMock(
            return_value=self._make_response_cm(200, {}, "ok")
        )

        await conn._make_request(
            AREndpoint.LOGIN,
            payload=payload,
            headers=None,
            request_type=request_type,
        )

        expected_url = f"http://{self._HOST}:{self._PORT}{url_suffix}"
        mock_session.request.assert_called_once_with(
            request_type.value,
            expected_url,
            data=expect_data,
            headers=self._DEFAULT_HEADERS,
            ssl=conn.config.get(ARCCKey.VERIFY_SSL),
        )

    async def test_custom_headers_override_default(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Custom headers replace self._header when provided."""

        conn = connection_factory()
        mock_session = self._setup_conn(conn)
        custom = {"x-custom": "yes"}
        mock_session.request = MagicMock(
            return_value=self._make_response_cm(200, {}, "ok")
        )

        await conn._make_request(
            AREndpoint.LOGIN, payload=None, headers=custom
        )

        assert mock_session.request.call_args.kwargs["headers"] == custom

    async def test_unicode_decode_error_retries_with_ignore(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Falls back to text(errors='ignore') on UnicodeDecodeError."""

        conn = connection_factory()
        mock_session = self._setup_conn(conn)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.text = AsyncMock(
            side_effect=[
                UnicodeDecodeError("utf-8", b"", 0, 1, "bad bytes"),
                "recovered",
            ]
        )
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response
        mock_cm.__aexit__.return_value = None
        mock_session.request = MagicMock(return_value=mock_cm)

        result = await conn._make_request(AREndpoint.LOGIN)

        assert result[2] == "recovered"
        mock_response.text.assert_called_with(errors="ignore")

    async def test_dumpback_called_on_response(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Calls dumpback with full response details when _dumpback is set."""

        conn = connection_factory()
        mock_session = self._setup_conn(conn)
        dumpback = AsyncMock()
        conn._dumpback = dumpback
        mock_session.request = MagicMock(
            return_value=self._make_response_cm(200, {"h": "v"}, "body")
        )

        await conn._make_request(AREndpoint.LOGIN, payload="p")

        dumpback.assert_awaited_once_with(
            AREndpoint.LOGIN, "p", 200, {"h": "v"}, "body"
        )

    async def test_no_dumpback_when_not_set(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Skips dumpback call when _dumpback is None."""

        conn = connection_factory()
        mock_session = self._setup_conn(conn)
        conn._dumpback = None
        mock_session.request = MagicMock(
            return_value=self._make_response_cm(200, {}, "ok")
        )

        result = await conn._make_request(AREndpoint.LOGIN)

        assert result == (200, {}, "ok")
