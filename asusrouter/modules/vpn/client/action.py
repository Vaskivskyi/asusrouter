"""VPN client action for AsusRouter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from asusrouter.modules.action import ARAction
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.service.action import (
    ARServiceInput,
    ARServiceResult,
    build_service_request,
    read_service_result,
)
from asusrouter.modules.vpn.client import classic, fusion
from asusrouter.modules.vpn.enums import ARVpnProtocol
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters_v2.raw import raw_to_str
from asusrouter.tools.types import ARCallbackType
from asusrouter.tools.writers import nvram

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity


class ARVpnClientAction(ARAction):
    """Enable or disable a VPN client of a given protocol and unit."""

    def __init__(
        self, protocol: ARVpnProtocol, state: bool, *, unit: int = 1
    ) -> None:
        """Initialize the action with the target client and desired state.

        `unit` is the per-protocol client unit (`wgc{unit}` / `vpn_client
        {unit}`), the same value the read source reports as `SERVER`.
        """

        super().__init__()

        self.protocol = protocol
        self.state = state
        self.unit = unit

    def __eq__(self, other: object) -> bool:
        """Equal by target protocol, unit and desired state."""

        if not isinstance(other, ARVpnClientAction):
            return NotImplemented
        return (
            self.protocol == other.protocol
            and self.unit == other.unit
            and self.state == other.state
        )

    def __hash__(self) -> int:
        """Hash by target protocol, unit and desired state."""

        return hash((type(self), self.protocol, self.unit, self.state))


async def _read_clientlist(callback: ARCallbackType) -> str | None:
    """Read the raw `vpnc_clientlist`, or None on a non-Fusion device."""

    request = f"hook={nvram(['vpnc_clientlist']) or ''}"
    data = await callback(endpoint=AREndpoint.FETCH_DATA, request=request)
    if not isinstance(data, dict):
        return None
    return raw_to_str(data.get("vpnc_clientlist"))


async def run_action(
    callback: ARCallbackType,
    action: ARVpnClientAction,
    *,
    raw_callback: ARCallbackType | None = None,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> ARServiceResult:
    """Toggle the action's VPN client on whichever backend the device uses."""

    clientlist = await _read_clientlist(callback)
    payload: tuple[list[ARServiceInput], dict[str, Any]] | None
    if clientlist is not None:
        payload = fusion.build_toggle_payload(
            clientlist, action.protocol, action.unit, action.state
        )
    else:
        payload = classic.build_toggle_payload(
            action.protocol, action.unit, action.state
        )

    if payload is None:
        return ARServiceResult(success=False)

    services, arguments = payload
    request = build_service_request(services, arguments=arguments)
    poster = raw_callback or callback
    data = await poster(endpoint=AREndpoint.PUSH_DATA, request=request)
    return read_service_result(data, services)


ARCallReg.register_action(ARVpnClientAction, run_action=run_action)


__all__ = [
    "ARVpnClientAction",
    "run_action",
]
