"""Tests for AsusRouter request-related methods."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from asusrouter.asusrouter import AsusRouter
from asusrouter.error import AsusRouter404Error, AsusRouterAccessError
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.endpoint.error import ARAccessError

_ENDPOINT = AREndpoint.FETCH_TEMPERATURE


@pytest.fixture
def conn(router: AsusRouter, monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Attach a mock connection to the router and return it."""

    connection = Mock()
    monkeypatch.setattr(router, "_connection", connection)
    return connection


class TestAsyncFetch:
    """Tests for AsusRouter.async_fetch."""

    async def test_returns_content_on_success(
        self, router: AsusRouter, conn: Mock
    ) -> None:
        """Returns the raw string content on a successful query."""

        conn.async_query = AsyncMock(return_value=(200, {}, "raw content"))

        assert await router.async_fetch(_ENDPOINT) == "raw content"

    async def test_404_returns_none_and_marks_unavailable(
        self, router: AsusRouter, conn: Mock
    ) -> None:
        """A 404 returns None and records the endpoint as unavailable."""

        conn.async_query = AsyncMock(side_effect=AsusRouter404Error)

        result = await router.async_fetch(_ENDPOINT)

        assert result is None
        assert _ENDPOINT in router._unavailable_endpoints

    async def test_redirect_page_returns_none_and_marks_unavailable(
        self, router: AsusRouter, conn: Mock
    ) -> None:
        """A 200 HTML redirect bounce is treated as an absent endpoint."""

        page = (
            '<HTML><HEAD><meta http-equiv="refresh" '
            'content="0; url=cloud_sync.asp?flag="></HEAD></HTML>'
        )
        conn.async_query = AsyncMock(return_value=(200, {}, page))

        result = await router.async_fetch(_ENDPOINT)

        assert result is None
        assert _ENDPOINT in router._unavailable_endpoints

    async def test_skips_known_unavailable_endpoint(
        self, router: AsusRouter, conn: Mock
    ) -> None:
        """A known-absent endpoint returns None without querying."""

        conn.async_query = AsyncMock(return_value=(200, {}, "content"))
        router._unavailable_endpoints.add(_ENDPOINT)

        result = await router.async_fetch(_ENDPOINT)

        assert result is None
        conn.async_query.assert_not_awaited()

    async def test_memoizes_404_across_calls(
        self, router: AsusRouter, conn: Mock
    ) -> None:
        """A 404 is remembered: the second call never hits the connection."""

        conn.async_query = AsyncMock(side_effect=AsusRouter404Error)

        first = await router.async_fetch(_ENDPOINT)
        second = await router.async_fetch(_ENDPOINT)

        assert first is None
        assert second is None
        conn.async_query.assert_awaited_once()

    async def test_retries_once_on_auth_error(
        self,
        router: AsusRouter,
        conn: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Drops the connection, sleeps 1s, then retries exactly once."""

        auth_error = AsusRouterAccessError("auth", ARAccessError.AUTHORIZATION)
        conn.async_query = AsyncMock(
            side_effect=[auth_error, (200, {}, "retried content")]
        )
        monkeypatch.setattr(router, "_async_drop_connection", Mock())

        with patch(
            "asusrouter.asusrouter.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            result = await router.async_fetch(_ENDPOINT)

        assert result == "retried content"
        assert conn.async_query.await_count == 2
        mock_sleep.assert_awaited_once_with(1)

    @pytest.mark.parametrize(
        "side_effect",
        [
            [
                AsusRouterAccessError("auth", ARAccessError.AUTHORIZATION),
                AsusRouterAccessError("auth", ARAccessError.AUTHORIZATION),
            ],
            AsusRouterAccessError("other", ARAccessError.CREDENTIALS),
        ],
        ids=["auth_error_twice", "non_auth_access_error"],
    )
    async def test_raises_access_error(
        self,
        router: AsusRouter,
        conn: Mock,
        monkeypatch: pytest.MonkeyPatch,
        side_effect: Any,
    ) -> None:
        """Re-raises a second auth error or any non-auth access error."""

        conn.async_query = AsyncMock(side_effect=side_effect)
        monkeypatch.setattr(router, "_async_drop_connection", Mock())

        with (
            patch(
                "asusrouter.asusrouter.asyncio.sleep", new_callable=AsyncMock
            ),
            pytest.raises(AsusRouterAccessError),
        ):
            await router.async_fetch(_ENDPOINT)


class TestAsyncRead:
    """Tests for AsusRouter.async_read."""

    async def test_returns_parsed_dict(
        self, router: AsusRouter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns the endpoint-reader result for valid content."""

        monkeypatch.setattr(
            router, "async_fetch", AsyncMock(return_value='{"key": "val"}')
        )

        assert await router.async_read(AREndpoint.FETCH_DATA) == {"key": "val"}

    @pytest.mark.parametrize(
        "content",
        [None, "", "   ", "﻿"],
        ids=["none", "empty", "whitespace", "bom"],
    )
    async def test_returns_empty_on_blank_content(
        self,
        router: AsusRouter,
        monkeypatch: pytest.MonkeyPatch,
        content: str | None,
    ) -> None:
        """Returns {} for empty or whitespace-only content."""

        monkeypatch.setattr(
            router, "async_fetch", AsyncMock(return_value=content)
        )

        assert await router.async_read(AREndpoint.FETCH_DATA) == {}

    async def test_dispatches_to_endpoint_reader(
        self, router: AsusRouter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Dispatches parsing to the reader registered for the endpoint."""

        monkeypatch.setattr(
            router, "async_fetch", AsyncMock(return_value="content")
        )
        fake_reader = Mock(return_value={"parsed": True})

        with patch(
            "asusrouter.asusrouter.get_endpoint_reader",
            return_value=fake_reader,
        ):
            result = await router.async_read(_ENDPOINT)

        fake_reader.assert_called_once_with("content")
        assert result == {"parsed": True}
