"""VPN server action for AsusRouter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from asusrouter.modules.action import ARAction
from asusrouter.modules.service.action import (
    ARServiceInput,
    ARServiceResult,
    async_run_service,
)
from asusrouter.modules.vpn.enums import ARVpnProtocol
from asusrouter.modules.vpn.server import openvpn, wireguard
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.types import ARCallbackType

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity


class ARVpnServerAction(ARAction):
    """Enable or disable a VPN server unit of a given protocol."""

    def __init__(
        self, protocol: ARVpnProtocol, state: bool, *, unit: int = 1
    ) -> None:
        """Initialize the action with the target server and desired state."""

        super().__init__()

        self.protocol = protocol
        self.state = state
        self.unit = unit

    def __eq__(self, other: object) -> bool:
        """Equal by target protocol, unit and desired state."""

        if not isinstance(other, ARVpnServerAction):
            return NotImplemented
        return (
            self.protocol == other.protocol
            and self.unit == other.unit
            and self.state == other.state
        )

    def __hash__(self) -> int:
        """Hash by target protocol, unit and desired state."""

        return hash((type(self), self.protocol, self.unit, self.state))


def _build_payload(
    action: ARVpnServerAction, identity: ARDeviceIdentity | None
) -> tuple[list[ARServiceInput], dict[str, Any]] | None:
    """Build the `(services, arguments)` for the action's protocol, or None."""

    if action.protocol is ARVpnProtocol.WIREGUARD:
        return wireguard.build_toggle_payload(action.unit, action.state)
    if action.protocol is ARVpnProtocol.OPENVPN:
        return openvpn.build_toggle_payload(
            action.unit, action.state, identity
        )
    return None


async def run_action(
    callback: ARCallbackType,
    action: ARVpnServerAction,
    *,
    raw_callback: ARCallbackType | None = None,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> ARServiceResult:
    """Toggle the action's VPN server on its protocol backend."""

    payload = _build_payload(action, identity)
    if payload is None:
        return ARServiceResult(success=False)

    services, arguments = payload
    return await async_run_service(
        callback, services, arguments=arguments, raw_callback=raw_callback
    )


ARCallReg.register_action(ARVpnServerAction, run_action=run_action)


__all__ = [
    "ARVpnServerAction",
    "run_action",
]
