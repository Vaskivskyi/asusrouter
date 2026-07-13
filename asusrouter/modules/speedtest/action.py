"""SpeedTest action for AsusRouter."""

from __future__ import annotations

import time
from typing import Any

from asusrouter.modules.action import ARAction
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.service.action import ARServiceResult
from asusrouter.modules.speedtest.models import (
    EXE_TYPE_RUN,
    build_run_request,
    build_start_time_request,
    normalize_server_id,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.types import ARCallbackType


class ARSpeedTestAction(ARAction):
    """Run a speedtest."""

    def __init__(
        self,
        server_id: int | str | None = None,
        iface: str | None = None,
    ) -> None:
        """Initialize the action with an optional server and interface."""

        super().__init__()

        self.server_id = normalize_server_id(server_id)
        self.iface = iface

    def _key(self) -> tuple[Any, ...]:
        """Key by the chosen server and interface."""

        return (self.server_id, self.iface)


async def run_action(
    callback: ARCallbackType,
    action: ARSpeedTestAction,
    *,
    raw_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> ARServiceResult:
    """Trigger a speedtest run."""

    # Post raw: async_fetch returns None on failure and the (ignored) body on
    # success, while async_read would collapse a failed fetch to {} and hide it
    poster = raw_callback or callback

    # The start time is only stored for the WebUI display; result not checked
    await poster(
        endpoint=AREndpoint.SET_SPEEDTEST_START_TIME,
        request=build_start_time_request(int(time.time() * 1000)),
    )
    data = await poster(
        endpoint=AREndpoint.RUN_SPEEDTEST,
        request=build_run_request(
            EXE_TYPE_RUN, server_id=action.server_id, iface=action.iface
        ),
    )
    return ARServiceResult(success=data is not None)


ARCallReg.register_action(ARSpeedTestAction, run_action=run_action)


__all__ = [
    "ARSpeedTestAction",
    "run_action",
]
