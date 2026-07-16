"""Polling tools for AsusRouter."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")


async def async_poll_until(
    probe: Callable[..., Awaitable[T]],
    ready: Callable[[T], bool],
    *,
    interval: float = 1.0,
    attempts: int = 5,
    **kwargs: Any,
) -> T | None:
    """Call probe until ready(result) is true, else None after attempts."""

    for attempt in range(attempts):
        result = await probe(**kwargs)
        if ready(result):
            return result
        if attempt + 1 < attempts:
            await asyncio.sleep(interval)

    return None


__all__ = [
    "async_poll_until",
]
