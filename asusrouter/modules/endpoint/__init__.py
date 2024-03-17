"""Endpoint module for AsusRouter."""

from __future__ import annotations

import importlib
import logging
from enum import Enum
from types import ModuleType
from typing import Any, Awaitable, Callable, Optional

from asusrouter.error import AsusRouter404Error
from asusrouter.modules.data import AsusData, AsusDataState
from asusrouter.modules.firmware import Firmware
from asusrouter.modules.wlan import Wlan

_LOGGER = logging.getLogger(__name__)


class Endpoint(str, Enum):
    """Endpoint enum. These endpoints are used to receive data from the device."""

    DEVICEMAP = "ajax_status.xml"
    ETHERNET_PORTS = "ajax_ethernet_ports.asp"
    FIRMWARE = "detect_firmware.asp"
    FIRMWARE_NOTE = "release_note0.asp"
    FIRMWARE_NOTE_AIMESH = "release_note_amas.asp"
    HOOK = "appGet.cgi"
    NETWORKMAPD = "update_networkmapd.asp"
    ONBOARDING = "ajax_onboarding.asp"
    PORT_STATUS = "get_port_status.cgi"
    RGB = "light_effect.html"
    STATE = "state.js"
    SYSINFO = "ajax_sysinfo.asp"
    TEMPERATURE = "ajax_coretmp.asp"
    UPDATE_CLIENTS = "update_clients.asp"
    VPN = "ajax_vpn_status.asp"


class EndpointControl(str, Enum):
    """Control endpoint enum. These endpoints are used to set parameters to the device."""

    APPLY = "apply.cgi"
    COMMAND = "applyapp.cgi"
    LEDG = "set_ledg.cgi"


class EndpointService(str, Enum):
    """Service endpoints."""

    LOGIN = "login.cgi"
    LOGOUT = "Logout.asp"


def _get_module(endpoint: Endpoint | EndpointControl) -> Optional[ModuleType]:
    """Attempt to get the module for the endpoint."""

    try:
        # Get the module name from the endpoint
        module_name = f"asusrouter.modules.endpoint.{endpoint.name.lower()}"
        # Import the module
        submodule = importlib.import_module(module_name)
        # Return the module
        return submodule
    except ModuleNotFoundError:
        _LOGGER.debug("No module found for endpoint %s", endpoint)
        return None


def read(endpoint: Endpoint | EndpointControl, content: str) -> dict[str, Any]:
    """Read the data from an endpoint."""

    _LOGGER.debug("Reading data from endpoint %s", endpoint)

    # Get the module
    submodule = _get_module(endpoint)

    # Read the data if module found
    if submodule:
        return submodule.read(content)

    return {}


def process(
    endpoint: Endpoint,
    data: dict[str, Any],
    history: Optional[dict[AsusData, AsusDataState]] = None,
    firmware: Optional[Firmware] = None,
    wlan: Optional[list[Wlan]] = None,
) -> dict[AsusData, Any]:
    """Process the data from an endpoint."""

    _LOGGER.debug("Processing data from endpoint %s", endpoint)

    # Get the module
    submodule = _get_module(endpoint)

    # Process the data if module found
    if submodule:
        # Check if the submodule requires history
        require_history = getattr(submodule, "REQUIRE_HISTORY", False)
        if require_history:
            data_set(data, history=history)
        # Check if the submodule requires identity
        require_firmware = getattr(submodule, "REQUIRE_FIRMWARE", False)
        if require_firmware:
            data_set(data, firmware=firmware)
        # Check if the submodule requires wlan
        require_wlan = getattr(submodule, "REQUIRE_WLAN", False)
        if require_wlan:
            data_set(data, wlan=wlan)

        # Process the data
        return submodule.process(data)

    return {}


def data_set(data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Append the data to the data dict."""

    # Go through the kwargs and append the data
    for key, value in kwargs.items():
        data[key] = value

    # Return the data
    return data


def data_get(data: dict[str, Any], key: str) -> Optional[Any]:
    """Extract value from the data dict and update the data dict."""

    # Get the value
    value = data.get(key, None)

    # Remove the value from the data dict
    data.pop(key, None)

    # Return the value
    return value


async def check_available(
    endpoint: Endpoint, api_query: Callable[..., Awaitable[Any]]
) -> tuple[bool, Optional[Any]]:
    """Check whether the endpoint is available or returns 404."""

    try:
        status, _, content = await api_query(endpoint)
        if status == 200:
            return (True, content)
    except AsusRouter404Error:
        return (False, None)

    return (False, None)
