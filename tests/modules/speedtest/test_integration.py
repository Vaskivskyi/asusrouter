"""End-to-end tests for fetching the speedtest source through the router."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from asusrouter.asusrouter import AsusRouter
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.endpoint_v2.hooks import ARHook
from asusrouter.modules.speedtest import ARSpeedTestResult, ARSpeedTestSource

_RESULT_HOOK = ARHook.OOKLA_SPEEDTEST_RESULT.value


def _events(result_id: str) -> list[dict]:
    """Build a result stream ending in a result row with the given id."""

    return [
        {
            "type": "result",
            "result": {"id": result_id},
            "download": {"bandwidth": 1000},
        },
        {},
    ]


async def test_fetch_source_by_server_with_refresh(
    router: AsusRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fetching the source with refresh + server_id runs against that server.

    The run is triggered against the source's bound server and the fresh
    result is returned - the user-friendly one-call path.
    """

    source = ARSpeedTestSource(server_id=54112)

    reads: list[tuple[AREndpoint, str | None]] = []
    result_reads = {"count": 0}

    async def fake_read(
        *, endpoint: AREndpoint, request: str | None = None, **_: Any
    ) -> Any:
        reads.append((endpoint, request))
        if (
            endpoint == AREndpoint.FETCH_DATA
            and request is not None
            and _RESULT_HOOK in request
        ):
            # First read is the pre-run id, the next is the fresh result
            result_reads["count"] += 1
            result_id = "old" if result_reads["count"] == 1 else "new"
            return {_RESULT_HOOK: _events(result_id)}
        return {}

    async def fake_fetch(
        *, endpoint: AREndpoint, request: str | None = None, **_: Any
    ) -> Any:
        reads.append((endpoint, request))
        return ""

    monkeypatch.setattr(router, "async_read", AsyncMock(side_effect=fake_read))
    monkeypatch.setattr(
        router, "async_fetch", AsyncMock(side_effect=fake_fetch)
    )

    with (
        patch("asusrouter.modules.action.asyncio.sleep", AsyncMock()),
        patch("asusrouter.tools.poll.asyncio.sleep", AsyncMock()),
    ):
        result = await router.async_fetch_data(
            source,
            force=True,
            refresh=True,
        )

    # The run was triggered against the source's bound server
    exe = [r for r in reads if r[0] == AREndpoint.RUN_SPEEDTEST]
    assert exe == [(AREndpoint.RUN_SPEEDTEST, "type=&id=54112")]

    # The fresh result is returned
    content = result[source]
    assert isinstance(content, ARSpeedTestResult)
    assert content.result_id == "new"
