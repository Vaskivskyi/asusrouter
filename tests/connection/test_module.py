"""Tests for connection module — module-level functions."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from asusrouter.config import ARConfig, ARConfigKey as ARConfKey
from asusrouter.connection import (
    _check_response,
    _log_request,
    _payload_for_logging,
)
from asusrouter.error import AsusRouter404Error, AsusRouterAccessError
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.tools.security import ARSecurityLevel


class TestPayloadForLogging:
    """Tests for _payload_for_logging."""

    _SAFE = AREndpoint.LOGOUT
    _LOGIN = AREndpoint.LOGIN

    @pytest.mark.parametrize(
        ("level", "endpoint", "payload", "expected"),
        [
            (ARSecurityLevel.STRICT, _SAFE, "data", None),
            (ARSecurityLevel.UNSAFE, _LOGIN, "secret", None),
            (ARSecurityLevel.DEFAULT, _SAFE, "", None),
            (ARSecurityLevel.DEFAULT, _SAFE, None, None),
            (ARSecurityLevel.DEFAULT, _SAFE, "data", "data"),
            (ARSecurityLevel.SANITIZED, _SAFE, "data", "data"),
            (ARSecurityLevel.UNSAFE, _SAFE, "data", "data"),
        ],
        ids=[
            "strict_returns_none",
            "login_always_none",
            "empty_payload_none",
            "none_payload_none",
            "default_non_sensitive",
            "sanitized_non_sensitive",
            "unsafe_non_sensitive",
        ],
    )
    def test_non_sensitive_endpoint(
        self,
        level: ARSecurityLevel,
        endpoint: AREndpoint,
        payload: str | None,
        expected: str | None,
    ) -> None:
        """Returns payload or None based on level and endpoint."""

        with patch(
            "asusrouter.connection.get_endpoint_sensitive", return_value=False
        ):
            result = _payload_for_logging(level, endpoint, payload)

        assert result == expected

    @pytest.mark.parametrize(
        ("level", "expected"),
        [
            (ARSecurityLevel.DEFAULT, None),
            (ARSecurityLevel.SANITIZED, "[SANITIZED PLACEHOLDER]"),
            (ARSecurityLevel.UNSAFE, "secret"),
        ],
        ids=["default_blocks", "sanitized_sanitizes", "unsafe_raw"],
    )
    def test_sensitive_endpoint(
        self,
        level: ARSecurityLevel,
        expected: str | None,
    ) -> None:
        """Sensitive endpoints: blocked, sanitized, or raw per level."""

        with patch(
            "asusrouter.connection.get_endpoint_sensitive", return_value=True
        ):
            result = _payload_for_logging(level, AREndpoint.LOGOUT, "secret")

        assert result == expected


class TestLogRequest:
    """Tests for _log_request."""

    @pytest.mark.parametrize(
        ("payload_to_log", "expected_call"),
        [
            (
                None,
                ("Sending request to `%s`", AREndpoint.LOGIN),
            ),
            (
                "body",
                (
                    "Sending request to `%s` with payload: %s",
                    AREndpoint.LOGIN,
                    "body",
                ),
            ),
        ],
        ids=["no_payload", "with_payload"],
    )
    def test_log_format(
        self,
        payload_to_log: str | None,
        expected_call: tuple[object, ...],
    ) -> None:
        """Logs with or without payload string from _payload_for_logging."""

        ARConfig.set(ARConfKey.DEBUG_PAYLOAD, ARSecurityLevel.DEFAULT)

        with (
            patch(
                "asusrouter.connection._payload_for_logging",
                return_value=payload_to_log,
            ) as mock_plf,
            patch("asusrouter.connection._LOGGER") as mock_logger,
        ):
            _log_request(AREndpoint.LOGIN, "raw")

            mock_logger.debug.assert_called_once_with(*expected_call)
            mock_plf.assert_called_once_with(
                ARSecurityLevel.DEFAULT, AREndpoint.LOGIN, "raw"
            )


class TestCheckResponse:
    """Tests for _check_response."""

    @pytest.mark.parametrize(
        ("status", "content", "expected_exc"),
        [
            (200, "ok", None),
            (404, "", AsusRouter404Error),
            (403, "", AsusRouterAccessError),
        ],
        ids=["success", "not_found", "non_200"],
    )
    def test_status_handling(
        self,
        status: int,
        content: str,
        expected_exc: type[Exception] | None,
    ) -> None:
        """Raises on 404 and non-200; passes cleanly on 200."""

        if expected_exc:
            with pytest.raises(expected_exc):
                _check_response(AREndpoint.LOGIN, status, {}, content)
        else:
            _check_response(AREndpoint.LOGIN, status, {}, content)

    def test_error_status_calls_handle_access_error(self) -> None:
        """Calls handle_access_error when 'error_status' in 200 response."""

        content = '{"error_status": "8"}'
        with patch("asusrouter.connection.handle_access_error") as mock_handle:
            _check_response(AREndpoint.LOGIN, 200, {"h": "v"}, content)

            mock_handle.assert_called_once_with(
                AREndpoint.LOGIN, 200, {"h": "v"}, content
            )

    def test_no_error_status_skips_handle(self) -> None:
        """Does not call handle_access_error when content is clean."""

        with patch("asusrouter.connection.handle_access_error") as mock_handle:
            _check_response(AREndpoint.LOGIN, 200, {}, "all good")

            mock_handle.assert_not_called()
