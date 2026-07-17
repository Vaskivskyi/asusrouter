"""VPN client data source for AsusRouter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.endpoint.hooks import hook_request
from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.vpn.client import classic, fusion
from asusrouter.modules.vpn.enums import ARVpnClientField, ARVpnProtocol
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters.raw import raw_to_str
from asusrouter.tools.types import ARCallbackType

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity


class ARVpnClientSource(ARDataSource):
    """AsusRouter VPN client data source (router acting as a VPN client)."""


# Universal instance - preferred
ARVpnClientSourceUniversal: ARVpnClientSource = ARVpnClientSource()


def _is_fusion(data: dict[str, Any]) -> bool:
    """Whether the device exposes the VPN Fusion `vpnc_clientlist`."""

    return raw_to_str(data.get(ARNvramType.VPNC_CLIENTLIST.value)) is not None


async def fetch_state(
    callback: ARCallbackType,
    source: ARVpnClientSource,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> Any:
    """Fetch client status and config, falling back to the classic path."""

    items = list(dict.fromkeys(fusion.nvram_items() + classic.nvram_items()))
    request = hook_request(fusion.STATUS_HOOK, fusion.NONDEF_WAN_HOOK, *items)
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


ARCallReg.register_source(
    ARVpnClientSource, fetch_state=fetch_state, translate_state=translate_state
)


__all__ = [
    "ARVpnClientSource",
    "ARVpnClientSourceUniversal",
    "fetch_state",
    "translate_state",
]
