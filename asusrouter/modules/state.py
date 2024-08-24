"""State module."""

from __future__ import annotations

import importlib
import logging
from enum import Enum
from types import ModuleType
from typing import Any, Awaitable, Callable, Optional

from asusrouter.modules.aura import AsusAura
from asusrouter.modules.connection import ConnectionState
from asusrouter.modules.data import AsusData, AsusDataState
from asusrouter.modules.parental_control import (
    AsusBlockAll,
    AsusParentalControl,
    ParentalControlRule,
)
from asusrouter.modules.port_forwarding import AsusPortForwarding
from asusrouter.modules.system import AsusSystem
from asusrouter.modules.vpnc import AsusVPNC
from asusrouter.modules.wireguard import (
    AsusWireGuardClient,
    AsusWireGuardServer,
)
from asusrouter.modules.wlan import AsusWLAN
from asusrouter.tools.converters import get_enum_key_by_value

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
    AURA = AsusAura
    BLOCK_ALL = AsusBlockAll
    CONNECTION = ConnectionState
    LED = AsusLED
    OPENVPN_CLIENT = AsusOVPNClient
    OPENVPN_SERVER = AsusOVPNServer
    PARENTAL_CONTROL = AsusParentalControl
    PC_RULE = ParentalControlRule
    PORT_FORWARDING = AsusPortForwarding
    SYSTEM = AsusSystem
    VPNC = AsusVPNC
    WIREGUARD_CLIENT = AsusWireGuardClient
    WIREGUARD_SERVER = AsusWireGuardServer
    WLAN = AsusWLAN


AsusStateMap: dict[AsusState, Optional[AsusData]] = {
    AsusState.NONE: None,
    AsusState.AURA: AsusData.AURA,
    AsusState.BLOCK_ALL: AsusData.PARENTAL_CONTROL,
    AsusState.CONNECTION: None,
    AsusState.LED: AsusData.LED,
    AsusState.OPENVPN_CLIENT: AsusData.OPENVPN_CLIENT,
    AsusState.OPENVPN_SERVER: AsusData.OPENVPN_SERVER,
    AsusState.PARENTAL_CONTROL: AsusData.PARENTAL_CONTROL,
    AsusState.PC_RULE: AsusData.PARENTAL_CONTROL,
    AsusState.PORT_FORWARDING: AsusData.PORT_FORWARDING,
    AsusState.SYSTEM: AsusData.SYSTEM,
    AsusState.VPNC: AsusData.VPNC,
    AsusState.WIREGUARD_CLIENT: AsusData.WIREGUARD_CLIENT,
    AsusState.WIREGUARD_SERVER: AsusData.WIREGUARD_SERVER,
    AsusState.WLAN: AsusData.WLAN,
}


def add_conditional_state(state: AsusState, data: AsusData) -> None:
    """A callback to add / change AsusStateMap."""

    if not isinstance(state, AsusState) or not isinstance(data, AsusData):
        _LOGGER.debug("Invalid state or data type: %s -> %s", state, data)
        return

    AsusStateMap[state] = data
    _LOGGER.debug("Added conditional state rule: %s -> %s", state, data)


def get_datatype(state: Optional[Any]) -> Optional[AsusData]:
    """Get the datatype."""

    asus_state = get_enum_key_by_value(
        AsusState, type(state), default=AsusState.NONE
    )

    return AsusStateMap.get(asus_state)


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

    if module_name.endswith(("_client", "_server")):
        module_name = module_name[:-7]

    # Module path
    module_path = f"asusrouter.modules.{module_name}"

    try:
        # Import the module
        submodule = importlib.import_module(module_path)
        # Return the module
        return submodule
    except ModuleNotFoundError:
        _LOGGER.debug("No module found for state %s", state)
        return None


def _has_method(module: ModuleType, method: str) -> bool:
    """Check if the module has the method."""

    return hasattr(module, method) and callable(getattr(module, method))


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusState,
    **kwargs: Any,
) -> bool:
    """Set the state."""

    # Get the module
    submodule = _get_module(state)

    # Process the data if module found
    if submodule and _has_method(submodule, "set_state"):
        # Determine the extra parameter
        if getattr(submodule, "REQUIRE_STATE", False):
            kwargs["extra_param"] = kwargs.get("router_state")
        if getattr(submodule, "REQUIRE_IDENTITY", False):
            kwargs["extra_param"] = kwargs.get("identity")

        # Call the function with the determined parameters
        return await submodule.set_state(
            callback=callback,
            state=state,
            **kwargs,
        )

    return False


def save_state(
    state: AsusState,
    library: dict[AsusData, AsusDataState],
    needed_time: Optional[int] = None,
    last_id: Optional[int] = None,
) -> None:
    """Save the state."""

    # Get the correct data key
    datatype = get_datatype(state)
    if datatype is None or datatype not in library:
        return

    # Save the state
    library[datatype].update_state(state, last_id)
    library[datatype].offset_time(needed_time)


async def keep_state(
    callback: Callable[..., Awaitable[Any]],
    states: Optional[AsusState | list[AsusState]],
    **kwargs: Any,
) -> None:
    """Keep the state."""

    if states is None:
        return

    # Make sure the state is a list
    states = [states] if not isinstance(states, list) else states

    # Process each state
    awaitables = [
        submodule.keep_state(callback, state, **kwargs)
        for state in states
        if (submodule := _get_module(state))
        and _has_method(submodule, "keep_state")
    ]

    # Execute all awaitables
    for awaitable in awaitables:
        await awaitable
