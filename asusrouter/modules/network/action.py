"""Network action for AsusRouter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from asusrouter.modules.action import ARAction
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.network import legacy, sdn
from asusrouter.modules.network.enums import (
    ARNetworkBackend,
    ARNetworkField,
    ARNetworkType,
)
from asusrouter.modules.network.handle import ARNetworkHandle
from asusrouter.modules.service.action import (
    ARServiceResult,
    build_service_request,
    read_service_result,
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


async def _build_payload(
    callback: ARCallbackType, handle: ARNetworkHandle, state: bool
) -> tuple[str, dict[str, Any]] | None:
    """Build the `(rc_service, arguments)` for the backend, or None."""

    if handle.backend is ARNetworkBackend.SDN:
        raw_sdn_rl = await sdn.fetch_sdn_rl(callback)
        if raw_sdn_rl is None:
            return None
        return sdn.build_toggle_payload(raw_sdn_rl, handle, state)

    return legacy.build_toggle_payload(handle, state)


async def run_action(
    callback: ARCallbackType,
    action: ARNetworkAction,
    *,
    raw_callback: ARCallbackType | None = None,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> ARServiceResult:
    """Toggle the action's network on its backend."""

    payload = await _build_payload(callback, action.handle, action.state)
    if payload is None:
        return ARServiceResult(success=False)

    rc_service, arguments = payload
    request = build_service_request(rc_service, arguments=arguments)
    poster = raw_callback or callback
    data = await poster(endpoint=AREndpoint.PUSH_DATA, request=request)
    return read_service_result(data, rc_service)


ARCallReg.register_action(ARNetworkAction, run_action=run_action)


__all__ = [
    "ARNetworkAction",
    "find_handle_by_ssid",
    "run_action",
]
