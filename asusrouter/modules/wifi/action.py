"""WiFi action for AsusRouter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from asusrouter.modules.action import ARAction
from asusrouter.modules.common.command import ARService
from asusrouter.modules.service.action import (
    ARServiceResult,
    async_run_service,
)
from asusrouter.modules.wifi.enums import ARWiFiBand
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.types import ARCallbackType

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity


class ARWiFiAction(ARAction):
    """Enable or disable a WiFi radio band."""

    def __init__(self, band: ARWiFiBand, state: bool) -> None:
        """Initialize the action with the target band and desired state."""

        super().__init__()

        self.band = band
        self.state = state

    def _key(self) -> tuple[Any, ...]:
        """Key by the target band and desired state."""

        return (self.band, self.state)


async def run_action(
    callback: ARCallbackType,
    action: ARWiFiAction,
    *,
    fetch_raw_callback: ARCallbackType | None = None,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> ARServiceResult:
    """Toggle the radio of the action's band via `restart_wireless`."""

    wifi = identity.wifi if identity is not None else None
    if not wifi or action.band not in wifi:
        return ARServiceResult(success=False)

    unit = wifi[action.band]
    arguments = {f"wl{unit}_radio": int(action.state)}
    return await async_run_service(
        callback,
        ARService.WIRELESS_RESTART,
        arguments=arguments,
        fetch_raw_callback=fetch_raw_callback,
    )


ARCallReg.register_action(ARWiFiAction, run_action=run_action)


__all__ = [
    "ARWiFiAction",
    "run_action",
]
