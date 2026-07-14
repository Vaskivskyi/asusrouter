"""Tests for the block-all-devices action."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.parental_control.block_all.action import (
    ARBlockAllAction,
    run_action,
)
from asusrouter.modules.parental_control.block_all.source import (
    ARBlockAllSourceUniversal,
)


def _poster() -> AsyncMock:
    """Build a push callback that reports the firewall restart ran."""

    return AsyncMock(return_value={"run_service": "restart_firewall"})


def _payload(callback: AsyncMock) -> dict[str, Any]:
    """Decode the pushed request body."""

    request = callback.await_args.kwargs["request"]
    assert callback.await_args.kwargs["endpoint"] is AREndpoint.PUSH_DATA
    return json.loads(request)


class TestAction:
    """Tests for the block-all toggle action."""

    @pytest.mark.parametrize(("state", "expected"), [(True, 1), (False, 0)])
    async def test_toggle(self, state: bool, expected: int) -> None:
        """A toggle writes MULTIFILTER_BLOCK_ALL and restarts the firewall."""

        callback = _poster()
        result = await run_action(callback, ARBlockAllAction(state=state))

        payload = _payload(callback)
        assert payload["rc_service"] == "restart_firewall"
        assert payload["MULTIFILTER_BLOCK_ALL"] == expected
        assert result.success is True

    async def test_expire_on_success(self) -> None:
        """A successful toggle expires the source and its nvram item."""

        expire = AsyncMock()
        await run_action(
            _poster(), ARBlockAllAction(state=True), expire_callback=expire
        )

        expired = {call.args[0] for call in expire.await_args_list}
        assert ARBlockAllSourceUniversal in expired
        assert ARNvramType.PARENTAL_CONTROL_BLOCK_ALL in expired

    async def test_no_expire_on_failure(self) -> None:
        """A failed toggle leaves the cache untouched."""

        expire = AsyncMock()
        await run_action(
            AsyncMock(return_value=None),
            ARBlockAllAction(state=True),
            expire_callback=expire,
        )

        expire.assert_not_awaited()
