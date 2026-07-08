"""VPN client data source for AsusRouter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.endpoint_v2.hooks import hook_request
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.vpn.client import classic, fusion
from asusrouter.modules.vpn.enums import ARVpnClientField, ARVpnProtocol
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters_v2.raw import raw_to_str
from asusrouter.tools.types import ARCallbackType
from asusrouter.tools.writers import nvram

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity


class ARVpnClientSource(ARDataSource):
    """AsusRouter VPN client data source (router acting as a VPN client)."""


# Universal instance - preferred
ARVpnClientSourceUniversal: ARVpnClientSource = ARVpnClientSource()


def _is_fusion(data: dict[str, Any]) -> bool:
    """Whether the device exposes the VPN Fusion `vpnc_clientlist`."""

    return raw_to_str(data.get("vpnc_clientlist")) is not None


async def get_state(
    callback: ARCallbackType,
    source: ARVpnClientSource,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> Any:
    """Fetch client status and config, falling back to the classic path."""

    keys = list(dict.fromkeys(fusion.nvram_keys() + classic.nvram_keys()))
    hooks = hook_request(fusion.STATUS_HOOK, fusion.NONDEF_WAN_HOOK)
    request = f"{hooks};{nvram(keys) or ''}"
    data = await callback(endpoint=AREndpoint.FETCH_DATA, request=request)

    # Non-Fusion devices report OpenVPN clients through vpn.cgi instead
    if isinstance(data, dict) and not _is_fusion(data):
        data[classic.STATUS_KEY] = await callback(
            endpoint=AREndpoint.FETCH_VPN_STATUS
        )

    return data


def translate_state(
    data: Any,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[ARVpnProtocol, dict[int, dict[ARVpnClientField, Any]]]:
    """Translate raw data into VPN client profiles grouped by protocol."""

    if not isinstance(data, dict):
        return {}

    if _is_fusion(data):
        return fusion.translate(data)
    return classic.translate(data)


ARCallReg.register_module(
    ARVpnClientSource, get_state=get_state, translate_state=translate_state
)


__all__ = [
    "ARVpnClientSource",
    "ARVpnClientSourceUniversal",
    "get_state",
    "translate_state",
]
