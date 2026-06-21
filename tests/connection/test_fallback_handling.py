"""Tests for connection module — fallback handling."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from asusrouter.connection import ConnectionFallback
from asusrouter.connection_config import ARConnectionConfigKey as ARCCKey
from asusrouter.const import (
    DEFAULT_PORT_HTTP,
    DEFAULT_PORT_HTTPS,
    DEFAULT_TIMEOUT_FALLBACK,
)
from asusrouter.error import (
    AsusRouterConnectionError,
    AsusRouterFallbackError,
    AsusRouterFallbackForbiddenError,
    AsusRouterFallbackLoopError,
)
from asusrouter.modules.endpoint_v2 import AREndpoint
from tests.helpers import AsyncPatch, ConnectionFactory, SyncPatch

CUSTOM_HTTP = DEFAULT_PORT_HTTP + 5
CUSTOM_HTTPS = DEFAULT_PORT_HTTPS + 5


class TestNextFallbackConfig:
    """Tests for Connection._next_fallback_config."""

    @pytest.mark.parametrize(
        (
            "use_ssl",
            "port",
            "strict_ssl",
            "allow_upgrade",
            "used_fallbacks",
            "expected_config",
            "expected_mark",
        ),
        [
            (
                True,
                CUSTOM_HTTPS,
                False,
                False,
                set(),
                {ARCCKey.USE_SSL: True, ARCCKey.PORT: DEFAULT_PORT_HTTPS},
                ConnectionFallback.HTTPS,
            ),
            (
                True,
                DEFAULT_PORT_HTTPS,
                False,
                False,
                set(),
                {ARCCKey.USE_SSL: False, ARCCKey.PORT: DEFAULT_PORT_HTTP},
                ConnectionFallback.HTTP,
            ),
            (
                False,
                CUSTOM_HTTP,
                False,
                False,
                set(),
                {ARCCKey.USE_SSL: False, ARCCKey.PORT: DEFAULT_PORT_HTTP},
                ConnectionFallback.HTTP,
            ),
            (
                False,
                DEFAULT_PORT_HTTP,
                False,
                True,
                set(),
                {ARCCKey.USE_SSL: True, ARCCKey.PORT: DEFAULT_PORT_HTTPS},
                ConnectionFallback.HTTPS,
            ),
        ],
        ids=[
            "https_custom_to_default",
            "https_default_to_http",
            "http_custom_to_default",
            "http_default_upgrade",
        ],
    )
    def test_success_matrix(
        self,
        use_ssl: bool,
        port: int,
        strict_ssl: bool,
        allow_upgrade: bool,
        used_fallbacks: set[ConnectionFallback],
        expected_config: dict[ARCCKey, Any],
        expected_mark: ConnectionFallback,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Returns correct config dict and marks fallback as used."""

        conn = connection_factory()
        conn.config.set(ARCCKey.USE_SSL, use_ssl)
        conn.config.set(ARCCKey.PORT, port)
        conn.config.set(ARCCKey.STRICT_SSL, strict_ssl)
        conn.config.set(ARCCKey.ALLOW_UPGRADE_HTTP_TO_HTTPS, allow_upgrade)
        conn._used_fallbacks = used_fallbacks.copy()

        result = conn._next_fallback_config()

        assert result == expected_config
        assert expected_mark in conn._used_fallbacks

    @pytest.mark.parametrize(
        (
            "use_ssl",
            "port",
            "strict_ssl",
            "allow_upgrade",
            "used_fallbacks",
            "expected_exc",
        ),
        [
            (
                True,
                CUSTOM_HTTPS,
                False,
                False,
                {ConnectionFallback.HTTPS},
                AsusRouterFallbackLoopError,
            ),
            (
                True,
                DEFAULT_PORT_HTTPS,
                False,
                False,
                {ConnectionFallback.HTTP},
                AsusRouterFallbackLoopError,
            ),
            (
                True,
                DEFAULT_PORT_HTTPS,
                True,
                False,
                set(),
                AsusRouterFallbackForbiddenError,
            ),
            (
                False,
                CUSTOM_HTTP,
                False,
                False,
                {ConnectionFallback.HTTP},
                AsusRouterFallbackLoopError,
            ),
            (
                False,
                DEFAULT_PORT_HTTP,
                False,
                True,
                {ConnectionFallback.HTTPS},
                AsusRouterFallbackLoopError,
            ),
            (
                False,
                DEFAULT_PORT_HTTP,
                False,
                False,
                set(),
                AsusRouterFallbackError,
            ),
        ],
        ids=[
            "https_custom_loop",
            "https_default_loop",
            "https_default_strict_ssl",
            "http_custom_loop",
            "http_default_upgrade_loop",
            "http_default_no_fallback",
        ],
    )
    def test_error_matrix(
        self,
        use_ssl: bool,
        port: int,
        strict_ssl: bool,
        allow_upgrade: bool,
        used_fallbacks: set[ConnectionFallback],
        expected_exc: type[Exception],
        connection_factory: ConnectionFactory,
    ) -> None:
        """Raises expected exception for each blocked transition."""

        conn = connection_factory()
        conn.config.set(ARCCKey.USE_SSL, use_ssl)
        conn.config.set(ARCCKey.PORT, port)
        conn.config.set(ARCCKey.STRICT_SSL, strict_ssl)
        conn.config.set(ARCCKey.ALLOW_UPGRADE_HTTP_TO_HTTPS, allow_upgrade)
        conn._used_fallbacks = used_fallbacks.copy()

        with pytest.raises(expected_exc):
            conn._next_fallback_config()


class TestApplyFallback:
    """Tests for Connection._apply_fallback."""

    @pytest.mark.parametrize(
        ("config", "expected_ssl", "expected_port"),
        [
            (
                {ARCCKey.USE_SSL: False, ARCCKey.PORT: DEFAULT_PORT_HTTP},
                False,
                DEFAULT_PORT_HTTP,
            ),
            (
                {ARCCKey.USE_SSL: True, ARCCKey.PORT: DEFAULT_PORT_HTTPS},
                True,
                DEFAULT_PORT_HTTPS,
            ),
        ],
        ids=["to_http", "to_https"],
    )
    async def test_applies_config_and_reconnects(
        self,
        config: dict[ARCCKey, Any],
        expected_ssl: bool,
        expected_port: int,
        connection_factory: ConnectionFactory,
        reset_auth: SyncPatch,
        async_connect: AsyncPatch,
    ) -> None:
        """Sets each config key, resets auth, and reconnects."""

        conn = connection_factory()
        mock_reset = reset_auth(conn)
        mock_connect = async_connect(conn)

        await conn._apply_fallback(config)

        assert conn.config.get(ARCCKey.USE_SSL) == expected_ssl
        assert conn.config.get(ARCCKey.PORT) == expected_port
        mock_reset.assert_called_once()
        mock_connect.assert_awaited_once_with(
            t_overwrite=DEFAULT_TIMEOUT_FALLBACK,
            block_error=True,
        )

    async def test_cancels_inflight_connect(
        self,
        connection_factory: ConnectionFactory,
        reset_auth: SyncPatch,
        async_connect: AsyncPatch,
    ) -> None:
        """Cancels and awaits an in-flight connect task before reconnecting."""

        conn = connection_factory()
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def long_running() -> bool:
            started.set()
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                cancelled.set()
                raise
            return True

        conn._connect_task = asyncio.create_task(long_running())
        await started.wait()

        mock_reset = reset_auth(conn)
        async_connect(conn)

        config = {ARCCKey.USE_SSL: False, ARCCKey.PORT: DEFAULT_PORT_HTTP}
        await conn._apply_fallback(config)

        assert cancelled.is_set()
        mock_reset.assert_called_once()

    async def test_consumes_exception_from_cancelled_task(
        self,
        connection_factory: ConnectionFactory,
        async_connect: AsyncPatch,
        reset_auth: SyncPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Logs and swallows exception from a cancelled in-flight task."""

        conn = connection_factory()

        async def task_raises_on_cancel() -> bool:
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError as exc:
                raise RuntimeError("boom") from exc
            return True

        conn._connect_task = asyncio.create_task(task_raises_on_cancel())
        await asyncio.sleep(0)

        mock_reset = reset_auth(conn)
        mock_connect = async_connect(conn)
        caplog.set_level(logging.DEBUG, logger="asusrouter.connection")

        config = {ARCCKey.USE_SSL: False, ARCCKey.PORT: DEFAULT_PORT_HTTP}
        await conn._apply_fallback(config)
        await asyncio.sleep(0)  # let done-callback fire

        mock_reset.assert_called_once()
        mock_connect.assert_awaited_once()
        assert any(
            r.levelno == logging.DEBUG
            and r.getMessage().startswith(
                "In-flight connect task raised after cancel:"
            )
            for r in caplog.records
        )

    async def test_skips_cancel_and_reconnect_when_in_login_context(
        self,
        connection_factory: ConnectionFactory,
        reset_auth: SyncPatch,
        async_connect: AsyncPatch,
    ) -> None:
        """Does not cancel itself or reconnect when called from login task."""

        conn = connection_factory()
        mock_reset = reset_auth(conn)
        mock_connect = async_connect(conn)
        config = {ARCCKey.USE_SSL: False, ARCCKey.PORT: DEFAULT_PORT_HTTP}

        async def task_body() -> None:
            conn._connect_task = asyncio.current_task()
            await conn._apply_fallback(config)

        task = asyncio.create_task(task_body())
        await task

        assert not task.cancelled()
        mock_reset.assert_called_once()
        mock_connect.assert_not_called()

    async def test_raises_when_reconnect_fails(
        self,
        connection_factory: ConnectionFactory,
        reset_auth: SyncPatch,
        async_connect: AsyncPatch,
    ) -> None:
        """Raises AsusRouterConnectionError when fallback reconnect fails."""

        conn = connection_factory()
        reset_auth(conn)
        async_connect(conn, return_value=False)

        config = {ARCCKey.USE_SSL: False, ARCCKey.PORT: DEFAULT_PORT_HTTP}

        with pytest.raises(AsusRouterConnectionError):
            await conn._apply_fallback(config)


class TestHandleFallback:
    """Tests for Connection._handle_fallback."""

    async def test_selects_applies_and_retries(
        self,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Calls _next_fallback_config, _apply_fallback, then callback."""

        conn = connection_factory()
        fake_config = {
            ARCCKey.USE_SSL: False,
            ARCCKey.PORT: DEFAULT_PORT_HTTP,
        }
        mock_callback = AsyncMock(return_value=(200, {}, "ok"))

        with (
            patch.object(
                conn,
                "_next_fallback_config",
                return_value=fake_config,
            ) as mock_next,
            patch.object(
                conn, "_apply_fallback", new_callable=AsyncMock
            ) as mock_apply,
        ):
            result = await conn._handle_fallback(
                callback=mock_callback,
                endpoint=AREndpoint.LOGIN,
            )

        assert result == (200, {}, "ok")
        mock_next.assert_called_once_with()
        mock_apply.assert_awaited_once_with(fake_config)
        mock_callback.assert_awaited_once_with(endpoint=AREndpoint.LOGIN)
