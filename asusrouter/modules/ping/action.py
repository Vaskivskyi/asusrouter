"""Ping action for AsusRouter."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.action import ARAction
from asusrouter.modules.common.status import STATUS_CODE_KEY, ARStatusCode
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.service.action import ARServiceResult
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.types import ARCallbackType


class ARPingAction(ARAction):
    """Run a DNS ping against the configured targets."""


async def run_action(
    callback: ARCallbackType, action: ARPingAction, **kwargs: Any
) -> ARServiceResult:
    """Run a DNS ping against the configured targets."""

    data = await callback(endpoint=AREndpoint.RUN_PING, request=None)
    code = data.get(STATUS_CODE_KEY) if isinstance(data, dict) else None
    return ARServiceResult(
        success=ARStatusCode.from_value(code) is ARStatusCode.SUCCESS
    )


ARCallReg.register_action(ARPingAction, run_action=run_action)


__all__ = [
    "ARPingAction",
    "run_action",
]
