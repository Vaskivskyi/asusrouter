"""Tests for connection module — session management."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from asusrouter.connection import Connection
from asusrouter.const import DEFAULT_TIMEOUT
from tests.helpers import (
    TCONST_HOST,
    TCONST_PASS,
    TCONST_USER,
    ConnectionFactory,
)


class TestCreateSession:
    """Tests for Connection._create_session."""

    @pytest.mark.parametrize(
        "timeout",
        [10, 30, DEFAULT_TIMEOUT],
        ids=["short", "long", "default"],
    )
    def test_creates_session_with_correct_args(self, timeout: int) -> None:
        """Session uses TCPConnector, cookie jar, and instance timeout."""

        conn = Connection(
            TCONST_HOST, TCONST_USER, TCONST_PASS, timeout=timeout
        )
        with (
            patch("aiohttp.ClientSession") as mock_session,
            patch("aiohttp.TCPConnector") as mock_connector,
            patch("asusrouter.connection.get_cookie_jar") as mock_jar_fn,
        ):
            mock_jar = Mock()
            mock_jar_fn.return_value = mock_jar

            result = conn._create_session()

        assert conn._manage_session is True
        mock_connector.assert_called_once_with()
        mock_session.assert_called_once_with(
            connector=mock_connector.return_value,
            cookie_jar=mock_jar,
            timeout=aiohttp.ClientTimeout(total=timeout),
        )
        assert result is mock_session.return_value

    def test_sets_manage_session_true(
        self, connection_factory: ConnectionFactory
    ) -> None:
        """_manage_session flips from False to True on call."""

        conn = connection_factory()
        assert conn._manage_session is False
        with (
            patch("aiohttp.ClientSession"),
            patch("aiohttp.TCPConnector"),
            patch("asusrouter.connection.get_cookie_jar"),
        ):
            conn._create_session()
        assert conn._manage_session is True


class TestAsyncCloseSession:
    """Tests for Connection.async_close_session."""

    @pytest.mark.parametrize(
        ("manage_session", "has_session", "session_closed", "close_called"),
        [
            (True, True, False, True),  # managed + open session → close called
            (True, True, True, False),  # managed + already closed → skip
            (False, True, False, False),  # not managed → early return
            (True, False, False, False),  # no session → early return
        ],
        ids=["open_managed", "already_closed", "not_managed", "no_session"],
    )
    async def test_close_behavior(
        self,
        manage_session: bool,
        has_session: bool,
        session_closed: bool,
        close_called: bool,
        connection_factory: ConnectionFactory,
    ) -> None:
        """close() only runs for managed, open sessions."""

        conn = connection_factory()
        conn._manage_session = manage_session

        mock_session: AsyncMock | None = None
        if has_session:
            mock_session = AsyncMock()
            mock_session.closed = session_closed
            conn._session = mock_session
        else:
            conn._session = None

        await conn.async_close_session()

        if mock_session is not None:
            if close_called:
                mock_session.close.assert_awaited_once()
            else:
                mock_session.close.assert_not_awaited()
