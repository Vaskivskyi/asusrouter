"""Tests for the connection module / Part 6 / Logging."""

from unittest.mock import patch

import pytest

from asusrouter.config import ARConfig, ARConfigKey as ARConfKey
from asusrouter.modules.endpoint import (
    EndpointControl,
    EndpointService,
    EndpointType,
)
from asusrouter.tools.security import ARSecurityLevel
from tests.helpers import ConnectionFactory, SyncPatch


class TestConnectionLogging:
    """Test for the Connection class logging."""

    LOGIN_ENDPOINT = EndpointService.LOGIN
    SENSITIVE_ENDPOINT = EndpointControl.APPLY
    SAFE_ENDPOINT = EndpointService.LOGOUT

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("level", "endpoint", "payload", "expected"),
        [
            # STRICT: never log payloads
            (ARSecurityLevel.STRICT, SAFE_ENDPOINT, "not-a-secret", None),
            # Login: never log payload even in unsafe mode
            (ARSecurityLevel.UNSAFE, LOGIN_ENDPOINT, "top-secret", None),
            # DEFAULT: non-sensitive
            (
                ARSecurityLevel.DEFAULT,
                SAFE_ENDPOINT,
                "not-a-secret",
                "not-a-secret",
            ),
            # DEFAULT: sensitive
            (ARSecurityLevel.DEFAULT, SENSITIVE_ENDPOINT, "secret", None),
            # SANITIZED: non-sensitive
            (
                ARSecurityLevel.SANITIZED,
                SAFE_ENDPOINT,
                "not-a-secret",
                "not-a-secret",
            ),
            # SANITIZED: sensitive
            (
                ARSecurityLevel.SANITIZED,
                SENSITIVE_ENDPOINT,
                "secret",
                "[SANITIZED PLACEHOLDER]",
            ),
            # UNSAFE: non-sensitive
            (
                ARSecurityLevel.UNSAFE,
                SAFE_ENDPOINT,
                "not-a-secret",
                "not-a-secret",
            ),
            # UNSAFE: sensitive
            (ARSecurityLevel.UNSAFE, SENSITIVE_ENDPOINT, "secret", "secret"),
            # Empty payload
            (ARSecurityLevel.DEFAULT, SAFE_ENDPOINT, "", None),
            # None payload
            (ARSecurityLevel.DEFAULT, SAFE_ENDPOINT, None, None),
        ],
        ids=[
            "strict",
            "login",
            "default_safe",
            "default_sensitive",
            "sanitized_safe",
            "sanitized_sensitive",
            "unsafe_safe",
            "unsafe_sensitive",
            "empty_payload",
            "none_payload",
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
        ARConfig.set(ARConfKey.DEBUG_PAYLOAD, level)

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
