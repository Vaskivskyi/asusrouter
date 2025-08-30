"""Tests for the Error endpoint module."""

from unittest.mock import Mock

import pytest

from asusrouter.const import HTTPStatus
from asusrouter.error import (
    AsusRouterAccessError,
    AsusRouterLogoutError,
    AsusRouterRequestFormatError,
)
from asusrouter.modules.endpoint import error as endpoint_error
from asusrouter.modules.endpoint.error import AccessError, handle_access_error


def test_handle_access_error_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of access errors."""

    monkeypatch.setattr(
        endpoint_error,
        "read_json_content",
        Mock(return_value={"error_status": HTTPStatus.OK}),
    )

    # Should not raise
    handle_access_error(
        endpoint=None,  # type: ignore[arg-type]
        status=None,
        headers=None,
        content=None,
    )


@pytest.mark.parametrize(
    "bad_status",
    [HTTPStatus.JSON_BAD_FORMAT, HTTPStatus.JSON_BAD_REQUEST],
)
def test_handle_access_error_json_format_raises(
    bad_status: HTTPStatus, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test handling of JSON format errors."""

    monkeypatch.setattr(
        endpoint_error,
        "read_json_content",
        Mock(return_value={"error_status": bad_status}),
    )

    with pytest.raises(AsusRouterRequestFormatError):
        handle_access_error(
            endpoint=None,  # type: ignore[arg-type]
            status=None,
            headers=None,
            content=None,
        )


def test_handle_access_error_logout_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test handling of logout errors."""

    monkeypatch.setattr(
        endpoint_error,
        "read_json_content",
        Mock(return_value={"error_status": AccessError.LOGOUT}),
    )

    with pytest.raises(AsusRouterLogoutError):
        handle_access_error(
            endpoint=None,  # type: ignore[arg-type]
            status=None,
            headers=None,
            content=None,
        )


def test_handle_access_error_try_again_includes_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test handling of try again errors."""

    timeout = 42

    monkeypatch.setattr(
        endpoint_error,
        "read_json_content",
        Mock(
            return_value={
                "error_status": AccessError.TRY_AGAIN,
                "remaining_lock_time": str(timeout),
            }
        ),
    )

    with pytest.raises(AsusRouterAccessError) as exinfo:
        handle_access_error(
            endpoint=None,  # type: ignore[arg-type]
            status=None,
            headers=None,
            content=None,
        )

    ex = exinfo.value
    # raised with args: ("Access error", error_enum, attributes)
    assert ex.args[1] == AccessError.TRY_AGAIN
    assert isinstance(ex.args[2], dict)
    assert ex.args[2].get("timeout") == timeout


def test_handle_access_error_unknown_raises_access_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test handling of unknown errors."""

    monkeypatch.setattr(
        endpoint_error,
        "read_json_content",
        Mock(return_value={"error_status": 999}),
    )

    with pytest.raises(AsusRouterAccessError) as exinfo:
        handle_access_error(
            endpoint=None,  # type: ignore[arg-type]
            status=None,
            headers=None,
            content=None,
        )

    ex = exinfo.value
    assert ex.args[1] == AccessError.UNKNOWN
    assert ex.args[2] == {}
