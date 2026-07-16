"""Tests for the polling tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from asusrouter.tools.poll import async_poll_until


async def test_ready_first_attempt() -> None:
    """Returns immediately when the first probe is ready."""

    probe = AsyncMock(return_value=5)
    with patch("asusrouter.tools.poll.asyncio.sleep", AsyncMock()) as sleep:
        result = await async_poll_until(probe, lambda v: v == 5, attempts=3)

    assert result == 5
    probe.assert_awaited_once()
    sleep.assert_not_awaited()


async def test_ready_after_retries() -> None:
    """Polls until a later probe is ready, sleeping between attempts."""

    probe = AsyncMock(side_effect=[0, 0, 7])
    with patch("asusrouter.tools.poll.asyncio.sleep", AsyncMock()) as sleep:
        result = await async_poll_until(
            probe, lambda v: v == 7, interval=2.0, attempts=5
        )

    assert result == 7
    assert probe.await_count == 3
    assert sleep.await_count == 2
    sleep.assert_awaited_with(2.0)


async def test_never_ready_returns_none() -> None:
    """Returns None after exhausting attempts, without a trailing sleep."""

    probe = AsyncMock(return_value=0)
    with patch("asusrouter.tools.poll.asyncio.sleep", AsyncMock()) as sleep:
        result = await async_poll_until(probe, lambda v: v == 1, attempts=4)

    assert result is None
    assert probe.await_count == 4
    assert sleep.await_count == 3


async def test_kwargs_forwarded_to_probe() -> None:
    """Every probe call receives the forwarded kwargs."""

    probe = AsyncMock(return_value=1)
    with patch("asusrouter.tools.poll.asyncio.sleep", AsyncMock()):
        await async_poll_until(probe, lambda _: True, force=True, extra=2)

    probe.assert_awaited_once_with(force=True, extra=2)
