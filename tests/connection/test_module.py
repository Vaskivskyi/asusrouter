"""Tests for connection module — module-level functions."""

from __future__ import annotations

import asyncio
import contextlib
from unittest.mock import patch

import pytest

from asusrouter.connection import (
    _check_response,
    _consume_task_exception,
    _log_request,
)
from asusrouter.error import AsusRouter404Error, AsusRouterAccessError
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.tools.security import ARSecurityLevel, Sensitive


class TestConsumeTaskException:
    """Tests for _consume_task_exception."""

    @pytest.mark.asyncio
    async def test_retrieves_exception(self) -> None:
        """A failed task's exception is retrieved, not left dangling."""

        async def boom() -> bool:
            raise RuntimeError("down")

        task: asyncio.Task[bool] = asyncio.create_task(boom())
        with pytest.raises(RuntimeError):
            await task

        # Task is done with an exception; consuming it must not raise
        _consume_task_exception(task)
        assert task.exception() is not None

    @pytest.mark.asyncio
    async def test_ignores_cancelled(self) -> None:
        """A cancelled task is handled without raising."""

        async def forever() -> bool:
            await asyncio.Event().wait()
            return True

        task: asyncio.Task[bool] = asyncio.create_task(forever())
        await asyncio.sleep(0)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

        _consume_task_exception(task)


class TestLogRequest:
    """Tests for _log_request."""

    @pytest.mark.parametrize(
        "payload",
        [None, ""],
        ids=["none_payload", "empty_payload"],
    )
    def test_no_payload_logs_endpoint_only(self, payload: str | None) -> None:
        """A missing or empty payload logs only the endpoint."""

        with patch("asusrouter.connection._LOGGER") as mock_logger:
            mock_logger.isEnabledFor.return_value = True
            _log_request(AREndpoint.LOGIN, payload)

            mock_logger.debug.assert_called_once_with(
                "Sending request to `%s`", AREndpoint.LOGIN
            )

    def test_payload_wrapped_sensitive(self) -> None:
        """The payload is wrapped as Sensitive with the endpoint level."""

        with patch("asusrouter.connection._LOGGER") as mock_logger:
            mock_logger.isEnabledFor.return_value = True
            _log_request(AREndpoint.LOGIN, "raw")

            args = mock_logger.debug.call_args.args
            assert args[0] == "Sending request to `%s` with payload: %s"
            assert args[1] == AREndpoint.LOGIN
            wrapped = args[2]
            assert isinstance(wrapped, Sensitive)
            assert wrapped.value == "raw"
            # LOGIN payload is sensitive - only revealed at UNSAFE
            assert wrapped.reveal_level is ARSecurityLevel.UNSAFE

    def test_non_sensitive_endpoint_reveals_at_default(self) -> None:
        """A non-sensitive endpoint payload reveals from DEFAULT."""

        with patch("asusrouter.connection._LOGGER") as mock_logger:
            mock_logger.isEnabledFor.return_value = True
            _log_request(AREndpoint.LOGOUT, "raw")

            wrapped = mock_logger.debug.call_args.args[2]
            assert wrapped.reveal_level is ARSecurityLevel.DEFAULT

    def test_skips_work_when_debug_disabled(self) -> None:
        """Emits nothing when DEBUG is off."""

        with patch("asusrouter.connection._LOGGER") as mock_logger:
            mock_logger.isEnabledFor.return_value = False
            _log_request(AREndpoint.LOGIN, "raw")

            mock_logger.debug.assert_not_called()


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
