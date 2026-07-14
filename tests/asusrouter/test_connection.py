"""Tests for AsusRouter connection-related methods."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.asusrouter import AsusRouter
from asusrouter.modules.aimesh import ARAiMeshSourceUniversal
from asusrouter.modules.boottime import ARBoottimeSourceUniversal
from asusrouter.modules.device import ARDeviceSourceUniversal
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import AREndpoint
from tests.helpers import MakeStateFactory


@pytest.mark.asyncio
async def test_aenter_connects_and_returns_self(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """__aenter__ calls async_connect and returns the router instance."""

    monkeypatch.setattr(router, "async_connect", AsyncMock(return_value=True))
    result = await router.__aenter__()
    router.async_connect.assert_awaited_once()  # type: ignore[attr-defined]
    assert result is router


@pytest.mark.asyncio
async def test_aexit_calls_async_close(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """__aexit__ calls async_close regardless of exception state."""

    monkeypatch.setattr(router, "async_close", AsyncMock())
    await router.__aexit__(None, None, None)
    router.async_close.assert_awaited_once()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_async_close_disconnects_then_closes_connection(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """async_close calls async_disconnect then _connection.async_close."""

    call_order: list[str] = []

    async def mock_disconnect() -> bool:
        call_order.append("disconnect")
        return True

    conn = Mock()
    conn.async_close_session = AsyncMock(
        side_effect=lambda: call_order.append("close")
    )

    monkeypatch.setattr(router, "async_disconnect", mock_disconnect)
    monkeypatch.setattr(router, "_connection", conn)

    await router.async_close()

    assert call_order == ["disconnect", "close"]


@pytest.mark.asyncio
async def test_async_connect_returns_false_when_connection_fails(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """async_connect returns False when _connection.async_connect fails."""

    conn = Mock()
    conn.async_connect = AsyncMock(return_value=False)
    monkeypatch.setattr(router, "_connection", conn)

    result = await router.async_connect()

    assert result is False


@pytest.mark.asyncio
async def test_async_connect_fetches_data_and_identity_on_success(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """async_connect fetches data and identity when connection succeeds."""

    conn = Mock()
    conn.async_connect = AsyncMock(return_value=True)
    monkeypatch.setattr(router, "_connection", conn)
    fetch = AsyncMock(return_value={"source": "data"})
    monkeypatch.setattr(router, "async_fetch_data", fetch)

    result = await router.async_connect()

    # The device identity source is fetched on connect
    assert (ARDeviceSourceUniversal,) in [
        call.args for call in fetch.await_args_list
    ]
    assert result is True


@pytest.mark.asyncio
async def test_async_connect_seeds_aimesh_topology(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Connect seeds the AiMesh topology right after the identity."""

    conn = Mock()
    conn.async_connect = AsyncMock(return_value=True)
    monkeypatch.setattr(router, "_connection", conn)
    fetch = AsyncMock(return_value={"x": 1})
    monkeypatch.setattr(router, "async_fetch_data", fetch)

    await router.async_connect()

    assert (ARAiMeshSourceUniversal,) in [
        call.args for call in fetch.await_args_list
    ]


@pytest.mark.asyncio
async def test_async_connect_fetches_boottime_when_not_seeded(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Connect fetches the boot time when none is seeded in config."""

    conn = Mock()
    conn.async_connect = AsyncMock(return_value=True)
    monkeypatch.setattr(router, "_connection", conn)
    fetch = AsyncMock(return_value={"x": 1})
    monkeypatch.setattr(router, "async_fetch_data", fetch)

    await router.async_connect()

    assert (ARBoottimeSourceUniversal,) in [
        call.args for call in fetch.await_args_list
    ]


@pytest.mark.asyncio
async def test_async_connect_seeds_boottime_from_config(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
    make_state: MakeStateFactory,
) -> None:
    """A seeded boot time is assigned and the fetch is skipped."""

    boottime = datetime(2026, 1, 1, tzinfo=UTC)
    identity = ARDeviceIdentity()
    id_state = make_state(ARDeviceSourceUniversal)
    cast(Any, id_state)._content = identity
    router._data_states[ARDeviceSourceUniversal] = id_state

    conn = Mock()
    conn.async_connect = AsyncMock(return_value=True)
    monkeypatch.setattr(router, "_connection", conn)
    fetch = AsyncMock(return_value={"x": 1})
    monkeypatch.setattr(router, "async_fetch_data", fetch)
    monkeypatch.setattr(router._config, "get", lambda key: boottime)

    await router.async_connect()

    assert identity.boottime == boottime
    assert (ARBoottimeSourceUniversal,) not in [
        call.args for call in fetch.await_args_list
    ]


@pytest.mark.asyncio
async def test_async_connect_clears_unavailable_endpoints(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful connect re-evaluates endpoint availability."""

    router._unavailable_endpoints.add(AREndpoint.FETCH_TEMPERATURE)

    conn = Mock()
    conn.async_connect = AsyncMock(return_value=True)
    monkeypatch.setattr(router, "_connection", conn)
    monkeypatch.setattr(
        router, "async_fetch_data", AsyncMock(return_value={"x": 1})
    )

    await router.async_connect()

    assert router._unavailable_endpoints == set()


@pytest.mark.asyncio
async def test_async_connect_returns_false_when_no_device_data(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """async_connect returns False when device data fetch returns None."""

    conn = Mock()
    conn.async_connect = AsyncMock(return_value=True)
    monkeypatch.setattr(router, "_connection", conn)
    fetch = AsyncMock(return_value=None)
    monkeypatch.setattr(router, "async_fetch_data", fetch)

    result = await router.async_connect()

    # Only the device fetch runs; the post-fetch seeding is skipped
    assert fetch.await_count == 1
    assert result is False


@pytest.mark.asyncio
async def test_async_disconnect_calls_connection_and_returns_true(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """async_disconnect calls _connection.async_disconnect and returns True."""

    conn = Mock()
    conn.async_disconnect = AsyncMock()
    monkeypatch.setattr(router, "_connection", conn)

    result = await router.async_disconnect()

    conn.async_disconnect.assert_awaited_once()
    assert result is True


@pytest.mark.asyncio
async def test_async_disconnect_re_raises_exception(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """async_disconnect re-raises exceptions from the connection."""

    conn = Mock()
    conn.async_disconnect = AsyncMock(side_effect=RuntimeError("dropped"))
    monkeypatch.setattr(router, "_connection", conn)

    with pytest.raises(RuntimeError, match="dropped"):
        await router.async_disconnect()


def test_async_drop_connection_resets_connection(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_async_drop_connection calls reset_auth on the connection."""

    conn = Mock()
    monkeypatch.setattr(router, "_connection", conn)

    router._async_drop_connection()

    conn.reset_auth.assert_called_once()
