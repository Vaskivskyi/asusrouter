"""Tests for connection module — connection management."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from asusrouter.const import USER_AGENT
from asusrouter.error import (
    AsusRouterAccessError,
    AsusRouterError,
    AsusRouterLogoutError,
    AsusRouterSSLCertificateError,
)
from tests.helpers import AsyncPatch, ConnectionFactory, SyncPatch


class TestAsyncConnect:
    """Tests for Connection.async_connect."""

    async def test_already_connected_returns_true(
        self,
        connection_factory: ConnectionFactory,
        login: AsyncPatch,
    ) -> None:
        """Already connected — returns True without creating a task."""

        conn = connection_factory()
        conn._connected = True
        mock_login = login(conn)

        result = await conn.async_connect()

        assert result is True
        mock_login.assert_not_called()

    async def test_success(
        self,
        connection_factory: ConnectionFactory,
        login: AsyncPatch,
    ) -> None:
        """Returns True when the underlying login succeeds."""

        conn = connection_factory()
        login(conn, return_value=True)

        result = await conn.async_connect()

        assert result is True

    async def test_connected_during_lock_returns_true(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Returns True if another caller connects first."""

        conn = connection_factory()
        with patch.object(
            conn,
            "_ensure_connect_task",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await conn.async_connect()

        assert result is True

    async def test_timeout_returns_false(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Returns False when the connect attempt times out."""

        conn = connection_factory()

        async def slow_login() -> bool:
            await asyncio.sleep(100)
            return True

        with patch.object(conn, "_login", side_effect=slow_login):
            result = await conn.async_connect(t_overwrite=0.001)

        assert result is False

    async def test_t_overwrite_used_as_timeout(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """t_overwrite overrides the instance timeout."""

        conn = connection_factory(
            timeout=100
        )  # long default — must be ignored

        async def slow_login() -> bool:
            await asyncio.sleep(100)
            return True

        with patch.object(conn, "_login", side_effect=slow_login):
            result = await conn.async_connect(t_overwrite=0.001)

        assert result is False

    async def test_block_error_suppresses_timeout_log(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """block_error=True prevents the error log on timeout."""

        conn = connection_factory()

        async def slow_login() -> bool:
            await asyncio.sleep(100)
            return True

        with (
            patch.object(conn, "_login", side_effect=slow_login),
            patch("asusrouter.connection._LOGGER") as mock_logger,
        ):
            result = await conn.async_connect(
                t_overwrite=0.001, block_error=True
            )

        assert result is False
        mock_logger.error.assert_not_called()

    @pytest.mark.parametrize(
        "block_error", [False, True], ids=["logs", "silent"]
    )
    async def test_inner_cancel_returns_false(
        self,
        block_error: bool,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Returns False when the inner connect task is cancelled."""

        conn = connection_factory()
        with patch.object(
            conn,
            "_login",
            new_callable=AsyncMock,
            side_effect=asyncio.CancelledError(),
        ):
            result = await conn.async_connect(block_error=block_error)

        assert result is False

    async def test_outer_cancel_propagates(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """CancelledError propagates when the outer task is cancelled."""

        conn = connection_factory()
        started = asyncio.Event()

        async def blocking_login() -> bool:
            started.set()
            await asyncio.sleep(100)
            return True

        with patch.object(conn, "_login", side_effect=blocking_login):
            outer = asyncio.create_task(conn.async_connect())
            await started.wait()
            outer.cancel()
            with pytest.raises(asyncio.CancelledError):
                await outer

    async def test_login_returns_false_propagates(
        self,
        connection_factory: ConnectionFactory,
        login: AsyncPatch,
    ) -> None:
        """Returns False when _login completes with False (e.g. no token)."""

        conn = connection_factory()
        login(conn, return_value=False)

        result = await conn.async_connect()

        assert result is False
        assert conn._connected is False

    async def test_connect_task_cleared_after_completion(
        self,
        connection_factory: ConnectionFactory,
        login: AsyncPatch,
    ) -> None:
        """_connect_task is None after a successful connect."""

        conn = connection_factory()
        login(conn, return_value=True)

        await conn.async_connect()

        assert conn._connect_task is None

    async def test_concurrent_callers_share_one_task(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Concurrent callers reuse a single in-flight connect task."""

        conn = connection_factory()
        login_calls = 0
        started = asyncio.Event()

        async def count_login() -> bool:
            nonlocal login_calls
            login_calls += 1
            started.set()
            await asyncio.sleep(0)
            conn._connected = True
            return True

        with patch.object(conn, "_login", side_effect=count_login):
            await asyncio.gather(conn.async_connect(), conn.async_connect())

        assert login_calls == 1


class TestEnsureConnectTask:
    """Tests for Connection._ensure_connect_task."""

    async def test_returns_none_if_already_connected(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Returns None when already connected."""

        conn = connection_factory()
        conn._connected = True

        result = await conn._ensure_connect_task()

        assert result is None

    async def test_creates_new_task_when_none_exists(
        self,
        connection_factory: ConnectionFactory,
        login: AsyncPatch,
    ) -> None:
        """Creates and returns a new Task when _connect_task is None."""

        conn = connection_factory()
        login(conn, return_value=True)

        task = await conn._ensure_connect_task()

        assert task is not None
        assert isinstance(task, asyncio.Task)
        with contextlib.suppress(Exception):
            await task

    async def test_creates_new_task_when_previous_done(
        self,
        connection_factory: ConnectionFactory,
        login: AsyncPatch,
    ) -> None:
        """Creates a new Task and consumes a finished previous one."""

        conn = connection_factory()
        login(conn, return_value=True)
        done_task: asyncio.Task[bool] = Mock(spec=asyncio.Task)
        done_task.done.return_value = True  # type: ignore[attr-defined]
        done_task.cancelled.return_value = False  # type: ignore[attr-defined]
        done_task.result.return_value = True  # type: ignore[attr-defined]
        conn._connect_task = done_task

        task = await conn._ensure_connect_task()

        assert task is not None
        assert task is not done_task
        # Finished task's result is consumed to avoid "never retrieved".
        done_task.result.assert_called_once()  # type: ignore[attr-defined]
        with contextlib.suppress(Exception):
            await task

    async def test_consumes_exception_from_previous_done_task(
        self,
        connection_factory: ConnectionFactory,
        login: AsyncPatch,
    ) -> None:
        """Swallows an exception from a finished previous task."""

        conn = connection_factory()
        login(conn, return_value=True)
        done_task: asyncio.Task[bool] = Mock(spec=asyncio.Task)
        done_task.done.return_value = True  # type: ignore[attr-defined]
        done_task.cancelled.return_value = False  # type: ignore[attr-defined]
        done_task.result.side_effect = RuntimeError("boom")  # type: ignore[attr-defined]
        conn._connect_task = done_task

        task = await conn._ensure_connect_task()  # must not raise

        assert task is not None
        assert task is not done_task
        done_task.result.assert_called_once()  # type: ignore[attr-defined]
        with contextlib.suppress(Exception):
            await task

    async def test_reuses_running_task(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Returns the existing Task when it is still running."""

        conn = connection_factory()
        running_task: asyncio.Task[bool] = Mock(spec=asyncio.Task)
        running_task.done.return_value = False  # type: ignore[attr-defined]
        conn._connect_task = running_task

        task = await conn._ensure_connect_task()

        assert task is running_task


class TestClearConnectTask:
    """Tests for Connection._clear_connect_task."""

    def test_clears_done_task(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Clears _connect_task when the task is done and matches."""

        conn = connection_factory()
        task: asyncio.Task[bool] = Mock(spec=asyncio.Task)
        task.done.return_value = True  # type: ignore[attr-defined]
        task.cancelled.return_value = False  # type: ignore[attr-defined]
        task.result.return_value = True  # type: ignore[attr-defined]
        conn._connect_task = task

        conn._clear_connect_task(task)

        assert conn._connect_task is None

    def test_consumes_exception_without_raising(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Consumes an unhandled task exception without re-raising it."""

        conn = connection_factory()
        task: asyncio.Task[bool] = Mock(spec=asyncio.Task)
        task.done.return_value = True  # type: ignore[attr-defined]
        task.cancelled.return_value = False  # type: ignore[attr-defined]
        task.result.side_effect = RuntimeError("connect failed")  # type: ignore[attr-defined]
        conn._connect_task = task

        conn._clear_connect_task(task)  # must not raise

        assert conn._connect_task is None

    def test_skips_result_for_cancelled_task(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Does not call result() for a cancelled task."""

        conn = connection_factory()
        task: asyncio.Task[bool] = Mock(spec=asyncio.Task)
        task.done.return_value = True  # type: ignore[attr-defined]
        task.cancelled.return_value = True  # type: ignore[attr-defined]
        conn._connect_task = task

        conn._clear_connect_task(task)

        task.result.assert_not_called()  # type: ignore[attr-defined]
        assert conn._connect_task is None

    def test_does_not_clear_newer_task(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Does not clear _connect_task when a newer task has replaced it."""

        conn = connection_factory()
        old_task: asyncio.Task[bool] = Mock(spec=asyncio.Task)
        old_task.done.return_value = True  # type: ignore[attr-defined]
        old_task.cancelled.return_value = False  # type: ignore[attr-defined]
        old_task.result.return_value = True  # type: ignore[attr-defined]
        new_task: asyncio.Task[bool] = Mock(spec=asyncio.Task)
        conn._connect_task = new_task

        conn._clear_connect_task(old_task)

        assert conn._connect_task is new_task

    def test_no_action_when_task_not_done(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Does nothing when the task is still running."""

        conn = connection_factory()
        task: asyncio.Task[bool] = Mock(spec=asyncio.Task)
        task.done.return_value = False  # type: ignore[attr-defined]
        conn._connect_task = task

        conn._clear_connect_task(task)

        assert conn._connect_task is task


class TestLogin:
    """Tests for Connection._login."""

    async def test_already_connected_returns_true(
        self,
        connection_factory: ConnectionFactory,
        send_request: AsyncPatch,
    ) -> None:
        """Returns True immediately when already connected; no request sent."""

        conn = connection_factory()
        conn._connected = True
        mock_send = send_request(conn)

        result = await conn._login()

        assert result is True
        mock_send.assert_not_called()

    @pytest.mark.parametrize(
        ("send_side_effect", "expected_exc", "match"),
        [
            (
                AsusRouterSSLCertificateError("bad cert"),
                AsusRouterAccessError,
                "due to the SSL certificate error",
            ),
            (
                AsusRouterAccessError("denied"),
                AsusRouterAccessError,
                "denied",
            ),
            (
                AsusRouterError("generic"),
                AsusRouterError,
                "generic",
            ),
            (
                RuntimeError("unexpected"),
                RuntimeError,
                "unexpected",
            ),
        ],
        ids=[
            "ssl_error",
            "access_error",
            "asusrouter_error",
            "unexpected_error",
        ],
    )
    async def test_send_request_error_propagates(
        self,
        send_side_effect: Exception,
        expected_exc: type[Exception],
        match: str,
        connection_factory: ConnectionFactory,
        send_request: AsyncPatch,
    ) -> None:
        """Network errors propagate with the correct type and message."""

        conn = connection_factory()
        mock_send = send_request(conn)
        mock_send.side_effect = send_side_effect

        with pytest.raises(expected_exc, match=match):
            await conn._login()

    @pytest.mark.parametrize(
        ("response_body", "expected_result"),
        [
            ('{"asus_token": "tok123"}', True),
            ('{"other_key": "value"}', False),
            ("not-json", False),
            ("[1, 2, 3]", False),
        ],
        ids=["valid_token", "no_token_key", "invalid_json", "non_dict_json"],
    )
    async def test_response_handling(
        self,
        response_body: str,
        expected_result: bool,
        connection_factory: ConnectionFactory,
        send_request: AsyncPatch,
    ) -> None:
        """Returns True only when the response contains a valid asus_token."""

        conn = connection_factory()
        mock_send = send_request(conn)
        mock_send.return_value = (200, {}, response_body)

        result = await conn._login()

        assert result is expected_result

    async def test_success_sets_auth_state(
        self,
        connection_factory: ConnectionFactory,
        send_request: AsyncPatch,
    ) -> None:
        """On success: token, header, and connected flag are set."""

        conn = connection_factory()
        mock_send = send_request(conn)
        mock_send.return_value = (200, {}, '{"asus_token": "tok123"}')

        await conn._login()

        assert conn._connected is True
        assert conn._token == "tok123"
        assert conn._header == {
            "user-agent": USER_AGENT,
            "cookie": "asus_token=tok123",
        }

    async def test_race_does_not_overwrite_token(
        self,
        connection_factory: ConnectionFactory,
        send_request: AsyncPatch,
    ) -> None:
        """Winning token is kept when another task connects first."""

        conn = connection_factory()
        mock_send = send_request(conn)

        async def side_effect(*_: Any, **__: Any) -> tuple[int, dict, str]:
            conn._connected = True
            conn._token = "winning-token"
            return (200, {}, '{"asus_token": "late-token"}')

        mock_send.side_effect = side_effect

        result = await conn._login()

        assert result is True
        assert conn._token == "winning-token"


class TestAsyncDisconnect:
    """Tests for Connection.async_disconnect."""

    async def test_not_connected_returns_true(
        self,
        connection_factory: ConnectionFactory,
        send_request: AsyncPatch,
    ) -> None:
        """Returns True immediately without sending a request."""

        conn = connection_factory()
        conn._connected = False
        mock_send = send_request(conn)

        result = await conn.async_disconnect()

        assert result is True
        mock_send.assert_not_called()

    @pytest.mark.parametrize(
        ("side_effect", "return_value", "expected", "reset_called"),
        [
            (AsusRouterLogoutError("ok"), None, True, True),
            (AsusRouterError("fail"), None, False, False),
            (None, (200, {}, ""), True, True),
        ],
        ids=["logout_error_success", "asusrouter_error", "unexpected_200"],
    )
    async def test_disconnect_outcomes(
        self,
        side_effect: Exception | None,
        return_value: Any,
        expected: bool,
        reset_called: bool,
        connection_factory: ConnectionFactory,
        send_request: AsyncPatch,
        reset_auth: SyncPatch,
    ) -> None:
        """Covers the three possible outcomes of the LOGOUT request."""

        conn = connection_factory()
        conn._connected = True
        mock_send = send_request(conn)
        mock_reset = reset_auth(conn)
        if side_effect is not None:
            mock_send.side_effect = side_effect
        else:
            mock_send.return_value = return_value

        result = await conn.async_disconnect()

        assert result is expected
        if reset_called:
            mock_reset.assert_called_once()
        else:
            mock_reset.assert_not_called()

    async def test_cancels_and_awaits_inflight_connect_task(
        self,
        connection_factory: ConnectionFactory,
        send_request: AsyncPatch,
        reset_auth: SyncPatch,
    ) -> None:
        """In-flight connect task is cancelled before the logout request."""

        conn = connection_factory()
        conn._connected = True

        async def blocking() -> bool:
            await asyncio.sleep(100)
            return True

        inflight = asyncio.create_task(blocking())
        conn._connect_task = inflight
        mock_send = send_request(conn)
        mock_send.side_effect = AsusRouterLogoutError("ok")
        reset_auth(conn)

        await conn.async_disconnect()

        assert inflight.cancelled()
        assert conn._connect_task is None


class TestResetAuth:
    """Tests for Connection.reset_auth."""

    @pytest.mark.parametrize(
        ("connected", "token", "header", "expect_cleared"),
        [
            (True, "tok", {"user-agent": "ua"}, True),
            (False, "tok", {"user-agent": "ua"}, False),
        ],
        ids=["connected", "not_connected"],
    )
    def test_reset_auth(
        self,
        connected: bool,
        token: str | None,
        header: dict[str, str] | None,
        expect_cleared: bool,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Clears auth state only when connected; early-returns otherwise."""

        conn = connection_factory()
        conn._connected = connected
        conn._token = token
        conn._header = header

        conn.reset_auth()

        if expect_cleared:
            assert conn._connected is False
            assert conn._token is None
            assert conn._header is None
        else:
            assert conn._token == token
            assert conn._header == header
