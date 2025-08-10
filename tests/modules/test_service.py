"""Tests for the service module."""

from asusrouter.error import AsusRouterError, AsusRouterServiceError
from asusrouter.modules.service import async_call_service
import pytest


async def callback(arguments: dict[str, str]) -> dict[str, str]:
    """Test callback method."""

    result: dict[str, str] = {}
    service = arguments.get("rc_service")
    apply = arguments.get("action_mode")
    result["modify"] = "1" if apply == "apply" else "0"
    if service is not None:
        result["run_service"] = service

    return result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "service",
        "arguments",
        "apply",
        "expect_modify",
        "expected_result",
        "needed_time",
        "expected_last_id",
    ),
    [
        ("restart_httpd", None, True, True, True, None, None),  # Apply
        ("restart_httpd", None, False, True, False, None, None),  # Don't apply
        (
            "restart_httpd",
            None,
            True,
            False,
            True,
            None,
            None,
        ),  # Apply, don't expect modify
        (
            "restart_httpd",
            None,
            False,
            False,
            True,
            None,
            None,
        ),  # Don't apply, don't expect
        ("restart_httpd", {"id": "1"}, True, True, True, 5, 1),  # Provided ID
        (
            None,
            {"action_mode": "update_client_list"},
            False,
            False,
            True,
            None,
            None,
        ),  # Special service
    ],
)
async def test_async_call_service(  # noqa: PLR0913
    service: str | None,
    arguments: dict[str, str] | None,
    apply: bool,
    expect_modify: bool,
    expected_result: bool,
    needed_time: int | None,
    expected_last_id: int | None,
) -> None:
    """Test the async_call_service method."""

    result, result_needed_time, last_id = await async_call_service(
        callback, service, arguments, apply, expect_modify
    )

    assert result == expected_result
    assert result_needed_time == needed_time
    assert last_id == expected_last_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception",
    [
        ValueError,
        TypeError,
        RuntimeError,
        AsusRouterError,
        Exception,
    ],
)
async def test_async_call_service_failing_callback(
    exception: Exception,
) -> None:
    """Test the async_call_service method with a failing callback."""

    async def failing_callback(_):
        raise exception("Test exception")

    with pytest.raises(exception):
        await async_call_service(failing_callback, "restart_httpd")


@pytest.mark.asyncio
async def test_async_call_service_with_invalid_service() -> None:
    """Test the async_call_service method with an invalid service."""

    async def invalid_callback(_):
        return {"run_service": "invalid_service"}

    with pytest.raises(AsusRouterServiceError):
        await async_call_service(invalid_callback, "restart_httpd")
