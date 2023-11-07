"""State module."""

from __future__ import annotations

import importlib
import logging
from enum import Enum
from types import ModuleType
from typing import Any, Awaitable, Callable, Optional, Tuple

from asusrouter.modules.connection import ConnectionState
from asusrouter.modules.data import AsusData, AsusDataState
from asusrouter.modules.identity import AsusDevice
from asusrouter.modules.parental_control import AsusParentalControl
from asusrouter.modules.port_forwarding import AsusPortForwarding
from asusrouter.modules.system import AsusSystem
from asusrouter.modules.vpnc import AsusVPNC
from asusrouter.modules.wireguard import AsusWireGuardClient, AsusWireGuardServer
from asusrouter.modules.wlan import AsusWLAN

from .led import AsusLED
from .openvpn import AsusOVPNClient, AsusOVPNServer

_LOGGER = logging.getLogger(__name__)


class AsusStateNone(int, Enum):
    """Asus state none."""

    NONE = 0


# AsusState = Union[AsusLED, AsusOVPNClient, AsusOVPNServer, AsusStateNone]


class AsusState(Enum):
    """Asus state."""

    NONE = AsusStateNone
    CONNECTION = ConnectionState
    LED = AsusLED
    OPENVPN_CLIENT = AsusOVPNClient
    OPENVPN_SERVER = AsusOVPNServer
    PARENTAL_CONTROL = AsusParentalControl
    PORT_FORWARDING = AsusPortForwarding
    SYSTEM = AsusSystem
    VPNC = AsusVPNC
    WIREGUARD_CLIENT = AsusWireGuardClient
    WIREGUARD_SERVER = AsusWireGuardServer
    WLAN = AsusWLAN


AsusStateMap: dict[AsusState, Optional[AsusData]] = {
    AsusState.NONE: None,
    AsusState.CONNECTION: None,
    AsusState.LED: AsusData.LED,
    AsusState.OPENVPN_CLIENT: AsusData.OPENVPN,
    AsusState.OPENVPN_SERVER: AsusData.OPENVPN,
    AsusState.PARENTAL_CONTROL: AsusData.PARENTAL_CONTROL,
    AsusState.PORT_FORWARDING: AsusData.PORT_FORWARDING,
    AsusState.SYSTEM: AsusData.SYSTEM,
    AsusState.VPNC: AsusData.VPNC,
    AsusState.WIREGUARD_CLIENT: AsusData.WIREGUARD,
    AsusState.WIREGUARD_SERVER: AsusData.WIREGUARD,
    AsusState.WLAN: AsusData.WLAN,
}


def add_conditional_state(state: AsusState, data: AsusData) -> None:
    """A callback to add / change AsusStateMap."""

    AsusStateMap[state] = data
    _LOGGER.debug("Added conditional state rule: %s -> %s", state, data)


def get_datatype(state: Optional[Any]) -> Optional[AsusData]:
    """Get the datatype."""

    asus_state = AsusState(type(state))

    if state is not None:
        return AsusStateMap.get(asus_state)

    return None


def _get_module_name(state: AsusState) -> Optional[str]:
    """Get the module name."""

    module_class = get_datatype(state)
    if module_class:
        return module_class.value

    return None


def _get_module(state: AsusState) -> Optional[ModuleType]:
    """Get the module."""

    # Module name
    module_name = _get_module_name(state)
    if not module_name:
        return None

    # Module path
    module_path = f"asusrouter.modules.{module_name}"

    try:
        # Import the module
        submodule = importlib.import_module(module_path)
        # Return the module
        return submodule
    except ModuleNotFoundError:
        _LOGGER.debug("No module found for state %s", AsusState)
        return None


def _has_method(module: ModuleType, method: str) -> bool:
    """Check if the module has the method."""

    return hasattr(module, method) and callable(getattr(module, method))


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusState,
    arguments: Optional[dict[str, Any]] = None,
    expect_modify: bool = False,
    router_state: Optional[dict[AsusData, AsusDataState]] = None,
    identity: Optional[AsusDevice] = None,
) -> bool:
    """Set the state."""

    # Get the module
    submodule = _get_module(state)

    # Process the data if module found
    if submodule and _has_method(submodule, "set_state"):
        # Determine the extra parameter
        extra_param: Optional[dict[AsusData, AsusDataState] | AsusDevice] = None
        if getattr(submodule, "REQUIRE_STATE", False):
            extra_param = router_state
        elif getattr(submodule, "REQUIRE_IDENTITY", False):
            extra_param = identity

        # Call the function with the determined parameters
        return await submodule.set_state(
            callback, state, arguments, expect_modify, extra_param
        )

    return False


def save_state(
    state: AsusState,
    library: dict[AsusData, AsusDataState],
    needed_time: Optional[int] = None,
) -> None:
    """Save the state."""

    # Get the correct data key
    datatype = get_datatype(state)
    if datatype is None:
        return

    # Save the state
    if datatype:
        library[datatype].update_state(state)
        library[datatype].offset_time(needed_time)


async def keep_state(
    callback: Callable[..., Awaitable[Any]],
    states: Optional[AsusState | list[AsusState]],
    identity: Optional[AsusDevice],
) -> None:
    """Keep the state."""

    if states is None:
        return

    # Make sure the state is a list
    if not isinstance(states, list):
        states = [states]

    # Process each state
    for state in states:
        # Get the module
        submodule = _get_module(state)

        # Process the data if module found
        if submodule and _has_method(submodule, "keep_state"):
            await submodule.keep_state(callback, state, identity)
