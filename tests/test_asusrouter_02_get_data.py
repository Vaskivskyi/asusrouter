"""Tests for the asusrouter module / Part 2 / Get Data."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from asusrouter.asusrouter import AsusRouter
from asusrouter.error import AsusRouter404Error, AsusRouterAccessError
from asusrouter.modules.endpoint.error import AccessError
from asusrouter.modules.endpoint_v2 import AREndpoint


@pytest.mark.asyncio
async def test_async_fetch_returns_content(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """async_fetch returns raw string content on success."""

    conn = Mock()
    conn.async_query = AsyncMock(return_value=(200, {}, "raw content"))
    monkeypatch.setattr(router, "_connection", conn)

    result = await router.async_fetch(AREndpoint.FETCH_TEMPERATURE)

    assert result == "raw content"


@pytest.mark.asyncio
async def test_async_fetch_returns_none_on_404(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """async_fetch returns None when the endpoint returns 404."""

    conn = Mock()
    conn.async_query = AsyncMock(side_effect=AsusRouter404Error)
    monkeypatch.setattr(router, "_connection", conn)

    result = await router.async_fetch(AREndpoint.FETCH_TEMPERATURE)

    assert result is None


@pytest.mark.asyncio
async def test_async_fetch_retries_once_on_auth_error(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """async_fetch drops connection, sleeps 1s, retries exactly once."""

    auth_error = AsusRouterAccessError("auth", AccessError.AUTHORIZATION)
    conn = Mock()
    conn.async_query = AsyncMock(
        side_effect=[auth_error, (200, {}, "retried content")]
    )
    monkeypatch.setattr(router, "_connection", conn)
    monkeypatch.setattr(router, "_async_drop_connection", Mock())

    with patch(
        "asusrouter.asusrouter.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        result = await router.async_fetch(AREndpoint.FETCH_TEMPERATURE)

    assert result == "retried content"
    assert conn.async_query.await_count == 2
    mock_sleep.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_async_fetch_does_not_retry_auth_error_twice(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """async_fetch raises on second auth error without further retry."""

    auth_error = AsusRouterAccessError("auth", AccessError.AUTHORIZATION)
    conn = Mock()
    conn.async_query = AsyncMock(side_effect=[auth_error, auth_error])
    monkeypatch.setattr(router, "_connection", conn)
    monkeypatch.setattr(router, "_async_drop_connection", Mock())

    with (
        patch("asusrouter.asusrouter.asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(AsusRouterAccessError),
    ):
        await router.async_fetch(AREndpoint.FETCH_TEMPERATURE)


@pytest.mark.asyncio
async def test_async_fetch_raises_on_non_auth_access_error(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """async_fetch re-raises non-authorization access errors."""

    conn = Mock()
    conn.async_query = AsyncMock(
        side_effect=AsusRouterAccessError("other", AccessError.CREDENTIALS)
    )
    monkeypatch.setattr(router, "_connection", conn)

    with pytest.raises(AsusRouterAccessError):
        await router.async_fetch(AREndpoint.FETCH_TEMPERATURE)


@pytest.mark.asyncio
async def test_async_read_returns_parsed_dict(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """async_read returns the endpoint-reader result for valid content."""

    monkeypatch.setattr(
        router,
        "async_fetch",
        AsyncMock(return_value='{"key": "val"}'),
    )

    result = await router.async_read(AREndpoint.FETCH_DATA)

    assert result == {"key": "val"}


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_content", [None, "", "   ", "﻿"])
async def test_async_read_returns_empty_on_blank_content(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
    bad_content: str | None,
) -> None:
    """async_read returns {} for empty or whitespace-only content."""

    monkeypatch.setattr(
        router,
        "async_fetch",
        AsyncMock(return_value=bad_content),
    )

    result = await router.async_read(AREndpoint.FETCH_DATA)

    assert result == {}


@pytest.mark.asyncio
async def test_async_read_uses_endpoint_reader(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """async_read dispatches to the reader registered for the endpoint."""

    monkeypatch.setattr(
        router,
        "async_fetch",
        AsyncMock(return_value="content"),
    )
    fake_reader = Mock(return_value={"parsed": True})

    with patch(
        "asusrouter.asusrouter.get_endpoint_reader", return_value=fake_reader
    ):
        result = await router.async_read(AREndpoint.FETCH_TEMPERATURE)

    fake_reader.assert_called_once_with("content")
    assert result == {"parsed": True}
