"""VPN server data source for AsusRouter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.endpoint.hooks import hook_request
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.vpn.enums import ARVpnProtocol, ARVpnServerField
from asusrouter.modules.vpn.server import openvpn, wireguard
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.types import ARCallbackType

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity

# Protocol -> its backend module (each exposes `nvram_items` and `translate`)
_BACKENDS = {
    ARVpnProtocol.WIREGUARD: wireguard,
    ARVpnProtocol.OPENVPN: openvpn,
}


class ARVpnServerSource(ARDataSource):
    """AsusRouter VPN server data source (router-global, all protocols)."""


# Universal instance - preferred
ARVpnServerSourceUniversal: ARVpnServerSource = ARVpnServerSource()


async def get_state(
    callback: ARCallbackType,
    source: ARVpnServerSource,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> Any:
    """Fetch the status hook and nvram config for every VPN server."""

    items = [
        item
        for backend in _BACKENDS.values()
        for item in backend.nvram_items()
    ]

    request = hook_request(wireguard.HOOK, *items)
    data = await callback(endpoint=AREndpoint.FETCH_DATA, request=request)

    # OpenVPN connected clients live in a separate endpoint; only worth
    # fetching when the server is enabled
    if isinstance(data, dict) and openvpn.server_enabled(data):
        data[openvpn.CLIENT_STATUS_KEY] = await callback(
            endpoint=AREndpoint.FETCH_VPN_OPENVPN_STATUS
        )

    return data


def translate_state(
    data: Any,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[ARVpnProtocol, dict[int, dict[ARVpnServerField, Any]]]:
    """Translate raw data into VPN server profiles grouped by protocol."""

    if not isinstance(data, dict):
        return {}

    result: dict[ARVpnProtocol, dict[int, dict[ARVpnServerField, Any]]] = {}
    for protocol, backend in _BACKENDS.items():
        servers = backend.translate(data)
        if servers:
            result[protocol] = servers

    return result


ARCallReg.register_module(
    ARVpnServerSource, get_state=get_state, translate_state=translate_state
)


__all__ = [
    "ARVpnServerSource",
    "ARVpnServerSourceUniversal",
    "get_state",
    "translate_state",
]
