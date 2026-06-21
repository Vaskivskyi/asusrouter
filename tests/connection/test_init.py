"""Tests for connection module — module-level functions and Connection init."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from asusrouter.config.connection import (
    ARConnectionConfig,
    ARConnectionConfigKey as ARCCKey,
)
from asusrouter.connection import (
    Connection,
    ConnectionFallback,
    generate_credentials,
    sanitize_data,
)
from asusrouter.const import (
    DEFAULT_PORT_HTTP,
    DEFAULT_PORT_HTTPS,
    DEFAULT_TIMEOUT,
    USER_AGENT,
)
from tests.helpers import TCONST_HOST, TCONST_PASS, TCONST_USER


class TestConnectionFallback:
    """Tests for the ConnectionFallback enum."""

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (ConnectionFallback.HTTP, "http"),
            (ConnectionFallback.HTTPS, "https"),
        ],
    )
    def test_values(self, member: ConnectionFallback, value: str) -> None:
        """Each member equals its string value."""

        assert member == value


class TestGenerateCredentials:
    """Tests for generate_credentials."""

    @pytest.mark.parametrize(
        ("username", "password", "expected_payload"),
        [
            (TCONST_USER, TCONST_PASS, "login_authorization=dXNlcjpwYXNz"),
            ("admin", "secret", "login_authorization=YWRtaW46c2VjcmV0"),
            ("", "", "login_authorization=Og=="),
        ],
        ids=["standard", "other_credentials", "empty"],
    )
    def test_payload_base64(
        self, username: str, password: str, expected_payload: str
    ) -> None:
        """Payload is base64(user:pass) prefixed with login_authorization."""

        payload, _ = generate_credentials(username, password)
        assert payload == expected_payload

    def test_headers_contain_user_agent(self) -> None:
        """Headers always carry the USER_AGENT value."""

        _, headers = generate_credentials(TCONST_USER, TCONST_PASS)
        assert headers == {"user-agent": USER_AGENT}


class TestSanitizeData:
    """Tests for sanitize_data."""

    @pytest.mark.parametrize(
        "value",
        [None, "", "some sensitive payload"],
        ids=["none", "empty", "non_empty"],
    )
    def test_always_returns_placeholder(self, value: str | None) -> None:
        """Returns the fixed placeholder string regardless of input."""

        assert sanitize_data(value) == "[SANITIZED PLACEHOLDER]"


class TestConnectionInit:
    """Tests for Connection.__init__."""

    def test_credentials_stored(self) -> None:
        """Hostname, username, and password are stored verbatim."""

        conn = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        assert conn._hostname == TCONST_HOST
        assert conn._username == TCONST_USER
        assert conn._password == TCONST_PASS

    @pytest.mark.parametrize(
        ("port", "use_ssl", "expected_port"),
        [
            (None, False, DEFAULT_PORT_HTTP),
            (None, True, DEFAULT_PORT_HTTPS),
            (8080, False, 8080),
            (8553, True, 8553),
        ],
        ids=["default_http", "default_https", "custom_http", "custom_https"],
    )
    def test_port_resolution(
        self, port: int | None, use_ssl: bool, expected_port: int
    ) -> None:
        """Port resolves to the provided value or the protocol default."""

        conn = Connection(
            TCONST_HOST, TCONST_USER, TCONST_PASS, port=port, use_ssl=use_ssl
        )
        assert conn.port == expected_port
        assert conn.config.get(ARCCKey.USE_SSL) == use_ssl

    def test_timeout_none_falls_back_to_default(self) -> None:
        """timeout=None stores DEFAULT_TIMEOUT."""

        conn = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS, timeout=None)
        assert conn._timeout == DEFAULT_TIMEOUT

    def test_timeout_custom(self) -> None:
        """Explicit timeout value is stored as-is."""

        conn = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS, timeout=15)
        assert conn._timeout == 15

    def test_initial_auth_state(self) -> None:
        """Token, header, and connected flag start at their zero values."""

        conn = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        assert conn._token is None
        assert conn._header is None
        assert conn._connected is False

    def test_initial_task_state(self) -> None:
        """connect_task and used_fallbacks start empty."""

        conn = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        assert conn._connect_task is None
        assert conn._used_fallbacks == set()

    def test_locks_are_asyncio_locks(self) -> None:
        """Both locks are asyncio.Lock instances."""

        conn = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        assert isinstance(conn._connection_lock, asyncio.Lock)
        assert isinstance(conn._connect_task_lock, asyncio.Lock)

    def test_session_provided(self) -> None:
        """Provided session is stored; manage_session stays False."""

        session = Mock()
        conn = Connection(
            TCONST_HOST, TCONST_USER, TCONST_PASS, session=session
        )
        assert conn._session is session
        assert conn._manage_session is False

    def test_session_not_provided(self) -> None:
        """No session is created eagerly; manage_session stays False."""

        conn = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        assert conn._session is None
        assert conn._manage_session is False

    def test_dumpback_stored(self) -> None:
        """Dumpback callable is stored."""

        dumpback = Mock()
        conn = Connection(
            TCONST_HOST, TCONST_USER, TCONST_PASS, dumpback=dumpback
        )
        assert conn._dumpback is dumpback

    def test_dumpback_none_by_default(self) -> None:
        """Dumpback is None when not provided."""

        conn = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        assert conn._dumpback is None

    def test_config_applied(self) -> None:
        """Custom config dict is applied to the internal ARConnectionConfig."""

        config = {ARCCKey.ALLOW_FALLBACK: True}
        conn = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS, config=config)
        assert conn.config.get(ARCCKey.ALLOW_FALLBACK) is True

    def test_config_none_leaves_defaults(self) -> None:
        """config=None leaves all settings at their defaults."""

        conn = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS, config=None)
        assert conn.config.get(ARCCKey.ALLOW_FALLBACK) is False

    def test_config_is_aru_connection_config_instance(self) -> None:
        """Internal _config is an ARConnectionConfig object."""

        conn = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        assert isinstance(conn._config, ARConnectionConfig)


class TestConnectionContextManager:
    """Tests for Connection.__aenter__ and __aexit__."""

    async def test_aenter_calls_connect_and_returns_self(self) -> None:
        """__aenter__ calls async_connect and returns the connection object."""

        conn = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        with patch.object(
            Connection, "async_connect", new_callable=AsyncMock
        ) as mock_connect:
            result = await conn.__aenter__()
            mock_connect.assert_called_once()
            assert result is conn

    async def test_aexit_calls_close(self) -> None:
        """__aexit__ calls async_close."""

        conn = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        with patch.object(
            Connection, "async_close_session", new_callable=AsyncMock
        ) as mock_close:
            await conn.__aexit__(None, None, None)
            mock_close.assert_called_once()

    async def test_context_manager_flow(self) -> None:
        """Async with block calls connect on enter and close on exit."""

        conn = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        with (
            patch.object(
                Connection, "async_connect", new_callable=AsyncMock
            ) as mock_connect,
            patch.object(
                Connection, "async_close_session", new_callable=AsyncMock
            ) as mock_close,
        ):
            async with conn as ctx:
                assert ctx is conn
            mock_connect.assert_called_once()
            mock_close.assert_called_once()


class TestConnectionIsolation:
    """Verify that multiple Connection instances never share mutable state."""

    def test_configs_are_independent(self) -> None:
        """Mutating one instance's config does not affect another."""

        conn1 = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        conn2 = Connection("192.168.1.1", TCONST_USER, TCONST_PASS)
        conn1.config.set(ARCCKey.ALLOW_FALLBACK, True)
        assert conn2.config.get(ARCCKey.ALLOW_FALLBACK) is False

    def test_used_fallbacks_are_independent(self) -> None:
        """_used_fallbacks sets are separate objects per instance."""

        conn1 = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        conn2 = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        conn1._used_fallbacks.add(ConnectionFallback.HTTP)
        assert conn2._used_fallbacks == set()

    def test_locks_are_independent(self) -> None:
        """Each instance owns its own lock objects."""

        conn1 = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        conn2 = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        assert conn1._connection_lock is not conn2._connection_lock
        assert conn1._connect_task_lock is not conn2._connect_task_lock

    def test_credentials_are_independent(self) -> None:
        """Credentials are stored independently per instance."""

        conn1 = Connection("host1", "user1", "pass1")
        conn2 = Connection("host2", "user2", "pass2")
        assert conn1._hostname != conn2._hostname
        assert conn1._username != conn2._username
        assert conn1._password != conn2._password

    def test_connection_state_is_independent(self) -> None:
        """Setting _connected on one instance does not bleed into another."""

        conn1 = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        conn2 = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        conn1._connected = True
        assert conn2._connected is False

    def test_session_is_independent(self) -> None:
        """Each instance stores its own session reference."""

        session1 = Mock()
        session2 = Mock()
        conn1 = Connection(
            TCONST_HOST, TCONST_USER, TCONST_PASS, session=session1
        )
        conn2 = Connection(
            TCONST_HOST, TCONST_USER, TCONST_PASS, session=session2
        )
        assert conn1._session is session1
        assert conn2._session is session2
        assert conn1._session is not conn2._session

    def test_timeout_is_independent(self) -> None:
        """Timeout is stored independently per instance."""

        conn1 = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS, timeout=10)
        conn2 = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS, timeout=30)
        assert conn1._timeout != conn2._timeout
