"""Tests for the ping action."""

from __future__ import annotations

from unittest.mock import AsyncMock

from asusrouter.const import AR_CALL_RUN_ACTION
from asusrouter.modules.common.status import STATUS_CODE_KEY
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.ping import ARPingAction, run_action
from asusrouter.registry import ARCallableRegistry as ARCallReg


class TestPingAction:
    """Tests for the ping action."""

    def test_registered(self) -> None:
        """The action resolves to the module run_action callable."""

        assert (
            ARCallReg.get_callable(ARPingAction(), AR_CALL_RUN_ACTION)
            is run_action
        )


class TestRunAction:
    """Tests for run_action."""

    async def test_success(self) -> None:
        """A success status code reports True."""

        callback = AsyncMock(return_value={STATUS_CODE_KEY: "success"})

        result = await run_action(callback, ARPingAction())

        assert result.success is True
        callback.assert_awaited_once_with(
            endpoint=AREndpoint.RUN_PING, request=None
        )

    async def test_non_success_code(self) -> None:
        """A missing or other status code reports False."""

        callback = AsyncMock(return_value={STATUS_CODE_KEY: "error"})

        result = await run_action(callback, ARPingAction())
        assert result.success is False

    async def test_non_dict_response(self) -> None:
        """A non-dict response reports False."""

        callback = AsyncMock(return_value=None)

        result = await run_action(callback, ARPingAction())
        assert result.success is False
