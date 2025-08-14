"""Tests for the connection module / Part 4 / Fallback."""

from typing import Any

import pytest

from asusrouter.connection import ConnectionFallback
from asusrouter.connection_config import ARConnectionConfigKey as ARCCKey
from asusrouter.const import DEFAULT_PORT_HTTP, DEFAULT_PORT_HTTPS
from asusrouter.error import (
    AsusRouterFallbackError,
    AsusRouterFallbackForbiddenError,
    AsusRouterFallbackLoopError,
    AsusRouterNotImplementedError,
)
from asusrouter.modules.endpoint import EndpointService
from tests.helpers import AsyncPatch, ConnectionFactory, SyncPatch

CUSTOM_HTTP = DEFAULT_PORT_HTTP + 5
CUSTOM_HTTPS = DEFAULT_PORT_HTTPS + 5


CASES_ASYNC_HANDLE_FALLBACK = [
    # HTTPS @ Custom port -> HTTPS @ Default
    {
        "use_ssl": True,
        "port": CUSTOM_HTTPS,
        "strict_ssl": False,
        "allow_upgrade": False,
        "used_fallbacks": {},
        "expected_fallback": ConnectionFallback.HTTPS,
        "expect_exception": None,
    },
    # HTTPS @ Custom port, fallback already used -> Loop error
    {
        "use_ssl": True,
        "port": CUSTOM_HTTPS,
        "strict_ssl": False,
        "allow_upgrade": False,
        "used_fallbacks": {ConnectionFallback.HTTPS: True},
        "expected_fallback": None,
        "expect_exception": AsusRouterFallbackLoopError,
    },
    # HTTPS @ Default -> HTTP @ Default (STRICT_SSL not set)
    {
        "use_ssl": True,
        "port": DEFAULT_PORT_HTTPS,
        "strict_ssl": False,
        "allow_upgrade": False,
        "used_fallbacks": {},
        "expected_fallback": ConnectionFallback.HTTP,
        "expect_exception": None,
    },
    # HTTPS @ Default, fallback already used -> Loop error
    {
        "use_ssl": True,
        "port": DEFAULT_PORT_HTTPS,
        "strict_ssl": False,
        "allow_upgrade": False,
        "used_fallbacks": {ConnectionFallback.HTTP: True},
        "expected_fallback": None,
        "expect_exception": AsusRouterFallbackLoopError,
    },
    # HTTPS @ Default -> HTTP @ Default (STRICT_SSL set)
    {
        "use_ssl": True,
        "port": DEFAULT_PORT_HTTPS,
        "strict_ssl": True,
        "allow_upgrade": False,
        "used_fallbacks": {},
        "expected_fallback": None,
        "expect_exception": AsusRouterFallbackForbiddenError,
    },
    # HTTP @ Custom port -> HTTP @ Default
    {
        "use_ssl": False,
        "port": CUSTOM_HTTP,
        "strict_ssl": False,
        "allow_upgrade": False,
        "used_fallbacks": {},
        "expected_fallback": ConnectionFallback.HTTP,
        "expect_exception": None,
    },
    # HTTP @ Custom port, fallback already used -> Loop error
    {
        "use_ssl": False,
        "port": CUSTOM_HTTP,
        "strict_ssl": False,
        "allow_upgrade": False,
        "used_fallbacks": {ConnectionFallback.HTTP: True},
        "expected_fallback": None,
        "expect_exception": AsusRouterFallbackLoopError,
    },
    # HTTP @ Default -> HTTPS @ Default (upgrade allowed)
    {
        "use_ssl": False,
        "port": DEFAULT_PORT_HTTP,
        "strict_ssl": False,
        "allow_upgrade": True,
        "used_fallbacks": {},
        "expected_fallback": ConnectionFallback.HTTPS,
        "expect_exception": None,
    },
    # HTTP @ Default, upgrade fallback already used -> Loop error
    {
        "use_ssl": False,
        "port": DEFAULT_PORT_HTTP,
        "strict_ssl": False,
        "allow_upgrade": True,
        "used_fallbacks": {ConnectionFallback.HTTPS: True},
        "expected_fallback": None,
        "expect_exception": AsusRouterFallbackLoopError,
    },
    # HTTP @ Default -> fallback not possible
    {
        "use_ssl": False,
        "port": DEFAULT_PORT_HTTP,
        "strict_ssl": False,
        "allow_upgrade": False,
        "used_fallbacks": {},
        "expected_fallback": None,
        "expect_exception": AsusRouterFallbackError,
    },
]

CASES_FALLBACK = [
    # No fallback provided
    {
        "fallback_type": None,
        "expected_ssl": False,
        "expected_port": DEFAULT_PORT_HTTP,
        "expected_verify_ssl": None,  # Should not change
        "expect_exception": None,
    },
    # HTTP fallback
    {
        "fallback_type": ConnectionFallback.HTTP,
        "expected_ssl": False,
        "expected_port": DEFAULT_PORT_HTTP,
        "expected_verify_ssl": None,  # Should not change
        "expect_exception": None,
    },
    # HTTPS fallback
    {
        "fallback_type": ConnectionFallback.HTTPS,
        "expected_ssl": True,
        "expected_port": DEFAULT_PORT_HTTPS,
        "expected_verify_ssl": None,  # Should not change
        "expect_exception": None,
    },
    # HTTPS_UNSAFE fallback
    {
        "fallback_type": ConnectionFallback.HTTPS_UNSAFE,
        "expected_ssl": True,
        "expected_port": DEFAULT_PORT_HTTPS,
        "expected_verify_ssl": False,
        "expect_exception": None,
    },
    # Not implemented fallback
    {
        "fallback_type": "not_implemented",
        "expected_ssl": None,
        "expected_port": None,
        "expected_verify_ssl": None,
        "expect_exception": AsusRouterNotImplementedError,
    },
]


class TestConnectionFallback:
    """Tests for the Connection class fallbacks."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "case",
        CASES_ASYNC_HANDLE_FALLBACK,
        ids=[
            "https_custom_to_default",
            "https_custom_loop",
            "https_default_to_http",
            "https_default_loop",
            "https_default_strict_ssl",
            "http_custom_to_default",
            "http_custom_loop",
            "http_default_upgrade",
            "http_default_upgrade_loop",
            "http_default_no_fallback",
        ],
    )
    async def test_async_handle_fallback_matrix(
        self,
        case: dict[str, Any],
        connection_factory: ConnectionFactory,
        fallback: AsyncPatch,
        send_request: AsyncPatch,
    ) -> None:
        """Test _async_handle_fallback method."""

        # Create a connection
        connection = connection_factory()
        # Prepare and set configs
        config = {
            ARCCKey.PORT: case["port"],
            ARCCKey.USE_SSL: case["use_ssl"],
            ARCCKey.STRICT_SSL: case["strict_ssl"],
            ARCCKey.ALLOW_UPGRADE_HTTP_TO_HTTPS: case["allow_upgrade"],
        }
        for key, value in config.items():
            connection.config.set(key, value)
        # Set used fallbacks
        connection._used_fallbacks = case["used_fallbacks"].copy()

        # Fallback failed (exception expected)
        if case["expect_exception"] is not None:
            with pytest.raises(case["expect_exception"]):
                await connection._async_handle_fallback(
                    connection._send_request, endpoint=EndpointService.LOGIN
                )
        # Fallback successful
        else:
            mock_send_request = send_request(connection)
            mock_fallback = fallback(connection)

            await connection._async_handle_fallback(
                mock_send_request,
                endpoint=EndpointService.LOGIN,
            )
            mock_fallback.assert_awaited_once_with(
                fallback_type=case["expected_fallback"]
            )
            mock_send_request.assert_awaited_once_with(
                endpoint=EndpointService.LOGIN
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "case",
        CASES_FALLBACK,
        ids=[
            "no_fallback",
            "http",
            "https",
            "https_unsafe",
            "not_implemented",
        ],
    )
    async def test_fallback_function(
        self,
        case: dict[str, Any],
        connection_factory: ConnectionFactory,
        reset_connection: SyncPatch,
        async_connect: AsyncPatch,
    ) -> None:
        """Test _fallback method."""

        connection = connection_factory()
        # Set initial config values
        connection.config.set(
            ARCCKey.USE_SSL, not case.get("expected_ssl", False)
        )
        connection.config.set(ARCCKey.PORT, 9999)
        connection.config.set(ARCCKey.VERIFY_SSL, True)

        mock_reset = reset_connection(connection)
        mock_connect = async_connect(connection)

        if case["expect_exception"]:
            with pytest.raises(case["expect_exception"]):
                await connection._fallback(case["fallback_type"])
        else:
            await connection._fallback(case["fallback_type"])
            # Check that we handle empty fallback types with a default value
            fallback_type = case["fallback_type"] or ConnectionFallback.HTTP
            # Fallback type should be marked as used
            assert connection._used_fallbacks.get(fallback_type) is True
            # Config values should be updated
            assert (
                connection.config.get(ARCCKey.USE_SSL) == case["expected_ssl"]
            )
            assert connection.config.get(ARCCKey.PORT) == case["expected_port"]
            # VERIFY_SSL only for HTTPS_UNSAFE
            if case["expected_verify_ssl"] is not None:
                assert (
                    connection.config.get(ARCCKey.VERIFY_SSL)
                    == case["expected_verify_ssl"]
                )
            # Should call reset_connection and async_connect
            mock_reset.assert_called_once()
            mock_connect.assert_awaited_once()
