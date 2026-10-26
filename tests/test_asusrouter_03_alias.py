"""Tests for the asusrouter module / Part 3 / Aliased datatypes."""

import asyncio
from types import MethodType, SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.data import AsusData, AsusDataState

from .test_asusrouter_00_common import get_asusrouter_instance

CORES = 4


class FakeIdentity(SimpleNamespace):
    """Device identity returning None for any missing attribute."""

    def __getattr__(self, name: str) -> Any:
        """Return None for missing attributes."""

        return None


def make_router(jiffies: list[int]) -> tuple[Any, list[int]]:
    """Router with a fake `main` hook; `jiffies[0]` is the current counter."""

    router = get_asusrouter_instance()
    router._identity = FakeIdentity(wlan=[], services=[])  # type: ignore[assignment]
    for name in (
        "_check_prerequisites",
        "_check_postrequisites",
        "_check_flags",
    ):
        setattr(router, name, AsyncMock(return_value=None))

    calls = [0]

    async def fake_load(self: Any, endpoint: Any, request: str = "") -> Any:
        calls[0] += 1
        await asyncio.sleep(0.05)
        total = jiffies[0]
        cpu = {}
        for core in range(1, CORES + 1):
            cpu[f"cpu{core}_total"] = str(total)
            cpu[f"cpu{core}_usage"] = str(total // 100)
        return {
            "cpu_usage": cpu,
            "memory_usage": {
                "mem_total": "1048576",
                "mem_free": "262144",
                "mem_used": "786432",
            },
            "netdev": {},
        }

    router.async_api_load = MethodType(fake_load, router)  # type: ignore[method-assign]
    return router, calls


@pytest.mark.asyncio
async def test_alias_shares_request_with_target() -> None:
    """RAM / NETWORK polled together with CPU must not refetch `main`.

    A second overlapping request makes the CPU usage a diff over a few
    jiffies only (readings like 25 / 33 / 50 / 100 %).
    """

    jiffies = [100_000]
    router, calls = make_router(jiffies)

    # Prime the history
    await router.async_get_data(AsusData.CPU)
    assert calls[0] == 1

    for _ in range(3):
        # 30 s later (cache expired), the RAM / NETWORK pollers fire
        # slightly before the CPU one while the request is in flight
        jiffies[0] += 3000
        for state in router._state.values():
            state.timestamp -= router._cache_threshold * 2

        async def cpu() -> Any:
            await asyncio.sleep(0.01)
            # Counters keep running while the first request is in flight
            jiffies[0] += 3
            return await router.async_get_data(AsusData.CPU)

        before = calls[0]
        _, _, cpu_data = await asyncio.gather(
            router.async_get_data(AsusData.RAM),
            router.async_get_data(AsusData.NETWORK),
            cpu(),
        )

        assert calls[0] == before + 1
        assert cpu_data["total"]["usage"] == pytest.approx(1.0, abs=0.1)
        assert router._state[AsusData.RAM].data


def test_data_state_events_are_independent() -> None:
    """Each state must have its own event, not a shared default."""

    first = AsusDataState()
    second = AsusDataState()
    assert first.inactive_event is not second.inactive_event

    first.start()
    second.stop()
    assert not first.inactive_event.is_set()
