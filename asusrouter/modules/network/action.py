"""Network action for AsusRouter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from asusrouter.modules.action import ARAction
from asusrouter.modules.network import legacy, sdn
from asusrouter.modules.network.enums import (
    ARNetworkBackend,
    ARNetworkField,
    ARNetworkType,
)
from asusrouter.modules.network.handle import ARNetworkHandle
from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.service.action import (
    ARServiceResult,
    async_run_service,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.identifiers import Ssid
from asusrouter.tools.types import ARCallbackType

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity


def find_handle_by_ssid(
    networks: Mapping[ARNetworkType, list[dict[ARNetworkField, Any]]],
    ssid: Ssid | str,
) -> ARNetworkHandle | None:
    """Return the handle of the network matching `ssid` from read data."""

    for profiles in networks.values():
        for profile in profiles:
            if profile.get(ARNetworkField.SSID) == ssid:
                handle = profile.get(ARNetworkField.HANDLE)
                if isinstance(handle, ARNetworkHandle):
                    return handle
    return None


class ARNetworkAction(ARAction):
    """Enable or disable a network profile."""

    def __init__(self, handle: ARNetworkHandle, state: bool) -> None:
        """Initialize the action with the target profile and desired state."""

        super().__init__()

        self.handle = handle
        self.state = state

    def __eq__(self, other: object) -> bool:
        """Equal by target profile and desired state."""

        if not isinstance(other, ARNetworkAction):
            return NotImplemented
        return self.handle == other.handle and self.state == other.state

    def __hash__(self) -> int:
        """Hash by target profile and desired state."""

        return hash((type(self), self.handle, self.state))


async def _read_sdn_rl(get_data_callback: ARCallbackType | None) -> Any:
    """Read the raw `sdn_rl` rule list via the NVRAM module, or None."""

    if get_data_callback is None:
        return None
    values = await get_data_callback(ARNvramType.SDN_RL)
    if not isinstance(values, dict):
        return None
    return values.get(ARNvramType.SDN_RL)


async def _build_payload(
    get_data_callback: ARCallbackType | None,
    handle: ARNetworkHandle,
    state: bool,
) -> tuple[str, dict[str, Any]] | None:
    """Build the `(rc_service, arguments)` for the backend, or None."""

    if handle.backend is ARNetworkBackend.SDN:
        raw_sdn_rl = await _read_sdn_rl(get_data_callback)
        if raw_sdn_rl is None:
            return None
        return sdn.build_toggle_payload(raw_sdn_rl, handle, state)

    return legacy.build_toggle_payload(handle, state)


async def run_action(
    callback: ARCallbackType,
    action: ARNetworkAction,
    *,
    get_data_callback: ARCallbackType | None = None,
    raw_callback: ARCallbackType | None = None,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> ARServiceResult:
    """Toggle the action's network on its backend."""

    payload = await _build_payload(
        get_data_callback, action.handle, action.state
    )
    if payload is None:
        return ARServiceResult(success=False)

    rc_service, arguments = payload
    return await async_run_service(
        callback, rc_service, arguments=arguments, raw_callback=raw_callback
    )


ARCallReg.register_action(ARNetworkAction, run_action=run_action)


__all__ = [
    "ARNetworkAction",
    "find_handle_by_ssid",
    "run_action",
]
