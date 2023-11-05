"""VPNC module. This module is compatible with VPN Fusion in AsusWRT 388+."""

from __future__ import annotations

import logging
from enum import Enum, IntEnum
from typing import Any, Awaitable, Callable, Optional

from asusrouter.modules.data import AsusData, AsusDataState
from asusrouter.modules.openvpn import AsusOVPNClient
from asusrouter.modules.wireguard import AsusWireGuardClient

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
    OPENVPN = "OpenVPN"
    WIREGUARD = "WireGuard"


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusVPNC | AsusOVPNClient | AsusWireGuardClient,
    arguments: Optional[dict[str, Any]] = None,
    expect_modify: bool = False,
    router_state: Optional[dict[AsusData, AsusDataState]] = None,
) -> bool:
    """Set the VPN state."""

    # Match the state to call the correct function
    match state:
        case a if isinstance(a, AsusVPNC):
            return await set_state_vpnc(
                callback, a, arguments, expect_modify, router_state
            )
        case a if isinstance(a, (AsusOVPNClient, AsusWireGuardClient)):
            return await set_state_other(
                callback, a, arguments, expect_modify, router_state
            )
        case _:
            _LOGGER.debug("Unknown state %s. Cannot find proper handler", state.name)
            return False


async def set_state_vpnc(
    callback: Callable[..., Awaitable[bool]],
    state: AsusVPNC,
    arguments: Optional[dict[str, Any]] = None,
    expect_modify: bool = False,
    router_state: Optional[dict[AsusData, AsusDataState]] = None,
) -> bool:
    """Set the VPN Fusion state."""

    # Check if arguments are available
    if not arguments:
        arguments = {}

    # Get the unit from arguments
    vpnc_unit = arguments.get("vpnc_unit")
    if vpnc_unit is None:
        _LOGGER.debug("No VPN Fusion unit found in arguments")
        return False

    # Keep only the unit
    arguments = {"vpnc_unit": vpnc_unit}

    vpnc_clientlist = None

    # Get the raw state from router
    if router_state is not None:
        vpnc_clientlist_object = router_state.get(AsusData.VPNC_CLIENTLIST)
        if vpnc_clientlist_object is not None:
            vpnc_clientlist = vpnc_clientlist_object.data

    if not vpnc_clientlist or vpnc_clientlist == "":
        _LOGGER.debug("No VPN Fusion client list found in router state")
        return False

    # Get the correct service call
    match state:
        case AsusVPNC.ON:
            service = "restart_vpnc"
            binary_state = 1
        case AsusVPNC.OFF:
            service = "stop_vpnc"
            binary_state = 0
        case _:
            _LOGGER.debug("Unknown state %s", state)
            return False

    # Update the clientlist
    vpnc_clientlist = _get_argument_clientlist(vpnc_clientlist, vpnc_unit, binary_state)
    if not vpnc_clientlist:
        _LOGGER.debug("Something went wrong with creating a new clientlist")
        return False
    arguments["vpnc_clientlist"] = vpnc_clientlist

    _LOGGER.debug(
        "Triggering state set with parameters: service=%s, arguments=%s",
        service,
        arguments,
    )

    # Call the service
    return await callback(
        service, arguments=arguments, apply=True, expect_modify=expect_modify
    )


async def set_state_other(
    callback: Callable[..., Awaitable[bool]],
    state: AsusOVPNClient | AsusWireGuardClient,
    arguments: Optional[dict[str, Any]] = None,
    expect_modify: bool = False,
    router_state: Optional[dict[AsusData, AsusDataState]] = None,
) -> bool:
    """Set the Open VPN state."""

    # Check if arguments are available
    if not arguments:
        arguments = {}

    vpn_id = arguments.get("id")
    if not vpn_id:
        _LOGGER.debug("No VPN id found in arguments")
        return False

    vpnc_data = None
    if router_state is not None:
        vpnc = router_state.get(AsusData.VPNC)
        if vpnc is not None:
            vpnc_data = vpnc.data

    vpnc_unit = _find_vpnc_unit(vpnc_data, state, vpn_id)

    # Convert state
    vpnc_state = (
        AsusVPNC.ON
        if state in (AsusOVPNClient.ON, AsusWireGuardClient.ON)
        else AsusVPNC.OFF
    )

    return await set_state_vpnc(
        callback, vpnc_state, {"vpnc_unit": vpnc_unit}, expect_modify, router_state
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
