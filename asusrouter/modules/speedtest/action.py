"""SpeedTest action for AsusRouter."""

from __future__ import annotations

import time
from typing import Any

from asusrouter.modules.action import ARAction
from asusrouter.modules.endpoint_v2 import AREndpoint
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

    def __eq__(self, other: object) -> bool:
        """Equal by chosen server and interface."""

        if not isinstance(other, ARSpeedTestAction):
            return NotImplemented
        return (self.server_id, self.iface) == (other.server_id, other.iface)

    def __hash__(self) -> int:
        """Hash by type, server, and interface."""

        return hash((type(self), self.server_id, self.iface))


async def run_action(
    callback: ARCallbackType, action: ARSpeedTestAction, **kwargs: Any
) -> bool:
    """Trigger a speedtest run."""

    await callback(
        endpoint=AREndpoint.SET_SPEEDTEST_START_TIME,
        request=build_start_time_request(int(time.time() * 1000)),
    )
    await callback(
        endpoint=AREndpoint.RUN_SPEEDTEST,
        request=build_run_request(
            EXE_TYPE_RUN, server_id=action.server_id, iface=action.iface
        ),
    )
    return True


ARCallReg.register_action(ARSpeedTestAction, run_action=run_action)


__all__ = [
    "ARSpeedTestAction",
    "run_action",
]
