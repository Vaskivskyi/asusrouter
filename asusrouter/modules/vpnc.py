"""VPNC module. This module is compatible with VPN Fusion in AsusWRT 388+."""

from __future__ import annotations

import logging
from enum import Enum, IntEnum
from typing import Any, Awaitable, Callable, Optional

from asusrouter.modules.data import AsusData, AsusDataState
from asusrouter.modules.openvpn import AsusOVPNClient
from asusrouter.modules.wireguard import AsusWireGuardClient
from asusrouter.tools.converters import get_arguments

_LOGGER = logging.getLogger(__name__)


REQUIRE_STATE = True


class AsusVPNC(IntEnum):
    """Asus VPN Fusion state."""

    UNKNOWN = -999
    CONNECTING = 1
    CONNECTED = 2
    ERROR = 4
    DISCONNECTED = 5

    OFF = DISCONNECTED
    ON = CONNECTING


class AsusVPNType(str, Enum):
    """Asus VPN Fusion type."""

    UNKNOWN = "Unknown"
    L2TP = "L2TP"
    OPENVPN = "OpenVPN"
    PPTP = "PPTP"
    SURFSHARK = "Surfshark"
    WIREGUARD = "WireGuard"


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusVPNC | AsusOVPNClient | AsusWireGuardClient,
    **kwargs: Any,
) -> bool:
    """Set the VPN state."""

    # Match the state to call the correct function
    match state:
        case a if isinstance(a, AsusVPNC):
            return await set_state_vpnc(callback, a, **kwargs)
        case a if isinstance(a, (AsusOVPNClient, AsusWireGuardClient)):
            return await set_state_other(callback, a, **kwargs)
        case _:
            try:
                _LOGGER.debug(
                    "Unknown state %s. Cannot find proper handler", state.name
                )
            except AttributeError:
                _LOGGER.debug("Unknown state %s. Cannot find proper handler", state)
            return False


VPNC_STATE_MAPPING = {
    AsusVPNC.ON: ("restart_vpnc", 1),
    AsusVPNC.OFF: ("stop_vpnc", 0),
}


async def set_state_vpnc(
    callback: Callable[..., Awaitable[bool]],
    state: Optional[AsusVPNC],
    **kwargs: Any,
) -> bool:
    """Set the VPN Fusion state."""

    # Check if state is available
    if not isinstance(state, AsusVPNC):
        _LOGGER.debug("No state found in arguments")
        return False

    # Get the arguments
    vpnc_unit = get_arguments("vpnc_unit", **kwargs)

    if not isinstance(vpnc_unit, int):
        _LOGGER.debug("No VPN Fusion unit found in arguments")
        return False

    # Service arguments
    service_arguments: dict[str, Any] = {"vpnc_unit": vpnc_unit}

    # Get the raw state from router
    router_state = kwargs.get("router_state", {})

    # Clientlist is needed to update the state (all clients are in the list).
    # If not available, we cannot update the state.
    vpnc_clientlist = router_state.get(AsusData.VPNC_CLIENTLIST, AsusDataState()).data
    if not vpnc_clientlist or vpnc_clientlist == "":
        _LOGGER.debug("No VPN Fusion client list found in router state")
        return False

    # Get service and binary state
    service, binary_state = VPNC_STATE_MAPPING.get(state, (None, None))
    if service is None:
        _LOGGER.debug("Unknown state %s", state)
        return False

    # Update the clientlist
    vpnc_clientlist = _get_argument_clientlist(vpnc_clientlist, vpnc_unit, binary_state)
    if not vpnc_clientlist:
        _LOGGER.debug("Something went wrong with creating a new clientlist")
        return False

    service_arguments["vpnc_clientlist"] = vpnc_clientlist

    _LOGGER.debug(
        "Triggering state set with parameters: service=%s, arguments=%s",
        service,
        service_arguments,
    )

    # Call the service
    return await callback(
        service=service,
        arguments=service_arguments,
        apply=True,
        expect_modify=kwargs.get("expect_modify", False),
    )


OTHER_STATE_MAPPING = {
    AsusOVPNClient.ON: AsusVPNC.ON,
    AsusOVPNClient.OFF: AsusVPNC.OFF,
    AsusWireGuardClient.ON: AsusVPNC.ON,
    AsusWireGuardClient.OFF: AsusVPNC.OFF,
}


async def set_state_other(
    callback: Callable[..., Awaitable[bool]],
    state: AsusOVPNClient | AsusWireGuardClient,
    **kwargs: Any,
) -> bool:
    """Set the Open VPN state."""

    # Check if state is available
    if not isinstance(
        state, (AsusOVPNClient, AsusWireGuardClient)
    ) or not state.value in (0, 1):
        _LOGGER.debug("No state found in arguments")
        return False

    # Get the arguments
    vpn_id = get_arguments("id", **kwargs)

    if not isinstance(vpn_id, int):
        _LOGGER.debug("No VPN id found in arguments")
        return False

    # Get the raw state from router
    router_state = kwargs.get("router_state", {})

    # Clientlist is needed to update the state (all clients are in the list).
    # If not available, we cannot update the state.
    vpnc_data = router_state.get(AsusData.VPNC, AsusDataState()).data

    vpnc_unit = _find_vpnc_unit(
        vpnc_data=vpnc_data, client_type=state, client_id=vpn_id
    )

    # Convert state
    vpnc_state = OTHER_STATE_MAPPING.get(state)

    return await set_state_vpnc(
        callback=callback,
        state=vpnc_state,
        vpnc_unit=vpnc_unit,
        expect_modify=kwargs.get("expect_modify", False),
        router_state=router_state,
    )


def _get_argument_clientlist(
    clientlist: Optional[str], vpnc_unit: Optional[int], state: Optional[int]
) -> Optional[str]:
    """Generate the clientlist argument."""

    if not clientlist or clientlist == "" or vpnc_unit is None or state is None:
        return None

    # Split clientlist properly
    clients: list[str] = clientlist.split("<")
    if len(clients) <= vpnc_unit:
        return None
    client = clients[vpnc_unit]

    # In the client data get the 6th parameter which is the state
    client_param = client.split(">")
    client_param[5] = str(state)

    # Assemble client
    client = ">".join(client_param)
    # Assemble clientlist
    clients[vpnc_unit] = client
    clientlist = "<".join(clients)

    return clientlist


def _find_vpnc_unit(
    vpnc_data: Optional[dict[AsusVPNType, dict[int, dict[str, Any]]]],
    client_type: AsusOVPNClient | AsusWireGuardClient,
    client_id: int,
) -> Optional[int]:
    """Find vpnc unit by VPN client_id."""

    if vpnc_data is None:
        return None

    match client_type:
        case a if isinstance(a, AsusOVPNClient):
            search_type = AsusVPNType.OPENVPN
        case a if isinstance(a, AsusWireGuardClient):
            search_type = AsusVPNType.WIREGUARD
        case _:
            _LOGGER.debug("Unknown client type %s", client_type)
            return None

    if search_type not in vpnc_data:
        return None

    if client_id not in vpnc_data[search_type]:
        return None

    return vpnc_data[search_type][client_id].get("vpnc_unit")
