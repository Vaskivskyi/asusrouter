"""Tests for the connection module / Part 6 / Logging."""

from unittest.mock import patch

import pytest

from asusrouter.config import ARConfig, ARConfigKey
from asusrouter.modules.endpoint import (
    EndpointService,
    EndpointTools,
    EndpointType,
)
from asusrouter.tools.security import ARSecurityLevel
from tests.helpers import ConnectionFactory, SyncPatch


class TestConnectionLogging:
    """Test for the Connection class logging."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("level", "endpoint", "payload", "expected"),
        [
            # STRICT: never log payloads
            (ARSecurityLevel.STRICT, EndpointService.LOGOUT, "p", None),
            # DEFAULT: non-sensitive endpoints log payload
            (ARSecurityLevel.DEFAULT, EndpointService.LOGOUT, "p", "p"),
            # DEFAULT: sensitive endpoints do NOT log payload
            (ARSecurityLevel.DEFAULT, EndpointService.LOGIN, "secret", None),
            # SANITIZED: sensitive endpoints log placeholder
            (
                ARSecurityLevel.SANITIZED,
                EndpointService.LOGIN,
                "secret",
                "secret",
            ),
            # UNSAFE: sensitive endpoints log verbatim
            (
                ARSecurityLevel.UNSAFE,
                EndpointService.LOGIN,
                "secret",
                "secret",
            ),
            # SANITIZED/UNSAFE with None payload -> still None
            (ARSecurityLevel.SANITIZED, EndpointService.LOGIN, None, None),
            (ARSecurityLevel.UNSAFE, EndpointService.LOGIN, None, None),
            # DEFAULT with empty string cleaned -> None
            (ARSecurityLevel.DEFAULT, EndpointService.LOGOUT, "", None),
            # DEFAULT with non-sensitive tools endpoint
            (ARSecurityLevel.DEFAULT, EndpointTools.NETWORK, "np", "np"),
        ],
        ids=[
            "strict_logout",
            "default_logout",
            "default_login_sensitive",
            "sanitized_login_sensitive",
            "unsafe_login_sensitive",
            "sanitized_login_none",
            "unsafe_login_none",
            "default_logout_empty",
            "default_network",
        ],
    )
    async def test_payload_for_logging(
        self,
        level: ARSecurityLevel,
        endpoint: EndpointType,
        payload: str | None,
        expected: str | None,
        connection_factory: ConnectionFactory,
    ) -> None:
        """Test _payload_for_logging method."""

        conn = connection_factory()
        result = conn._payload_for_logging(level, endpoint, payload)
        assert result == expected

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("endpoint", "payload", "level"),
        [
            (EndpointService.LOGIN, "payload", ARSecurityLevel.DEFAULT),
            (EndpointService.LOGIN, None, ARSecurityLevel.SANITIZED),
        ],
    )
    async def test_log_request(
        self,
        endpoint: EndpointType,
        payload: str | None,
        level: ARSecurityLevel,
        connection_factory: ConnectionFactory,
        payload_for_logging: SyncPatch,
    ) -> None:
        """Test _log_request method."""

        connection = connection_factory()

        # Set logging config
        ARConfig.set(ARConfigKey.DEBUG_PAYLOAD, level)

        # Prepare a mock for payload preparation
        mock_payload_for_logging = payload_for_logging(connection)
        mock_payload_for_logging.return_value = payload

        # Mock the logger
        with patch("asusrouter.connection._LOGGER.debug") as mock_logger:
            # Call the method
            connection._log_request(endpoint, payload)

            # Check that a correct log message was generated
            if payload is not None:
                mock_logger.assert_called_once_with(
                    "Sending request to `%s` with payload: %s",
                    endpoint,
                    payload,
                )
            else:
                mock_logger.assert_called_once_with(
                    "Sending request to `%s`", endpoint
                )

            mock_payload_for_logging.assert_called_once_with(
                level, endpoint, payload
            )
