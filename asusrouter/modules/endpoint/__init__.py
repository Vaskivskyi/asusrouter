"""Endpoint module for AsusRouter."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import importlib
import logging
from types import ModuleType
from typing import Any, Final

from asusrouter.const import HTTPStatus, RequestType
from asusrouter.error import AsusRouter404Error
from asusrouter.modules.data import AsusData, AsusDataState
from asusrouter.modules.firmware import Firmware
from asusrouter.modules.wlan import Wlan

_LOGGER = logging.getLogger(__name__)


class Endpoint(str, Enum):
    """Endpoint enum.

    These endpoints are used to receive data from the device.
    """

    CERT_INFO = "ajax_certinfo.asp"
    DDNS_CODE = "ajax_ddnscode.asp"
    DEVICEMAP = "ajax_status.xml"
    DSL = "ajax_AdslStatus.asp"
    ETHERNET_PORTS = "ajax_ethernet_ports.asp"
    FIRMWARE = "detect_firmware.asp"
    FIRMWARE_NOTE = "release_note0.asp"
    FIRMWARE_NOTE_AIMESH = "release_note_amas.asp"
    HOOK = "appGet.cgi"
    NETWORKMAPD = "update_networkmapd.asp"
    ONBOARDING = "ajax_onboarding.asp"
    PORT_STATUS = "get_port_status.cgi"
    STATE = "state.js"
    SYSINFO = "ajax_sysinfo.asp"
    TEMPERATURE = "ajax_coretmp.asp"
    UPDATE_CLIENTS = "update_clients.asp"
    VPN = "ajax_vpn_status.asp"
    # Endpoints known but not used / not available on test devices
    # RGB = "light_effect.html"


class EndpointControl(str, Enum):
    """Control endpoint enum.

    These endpoints are used to set parameters to the device.
    """

    APPLY = "apply.cgi"
    COMMAND = "applyapp.cgi"


class EndpointService(str, Enum):
    """Service endpoints."""

    LOGIN = "login.cgi"
    LOGOUT = "Logout.asp"


class EndpointTools(str, Enum):
    """Tools endpoints."""

    # AURA control / RGB
    AURA = "set_ledg.cgi"
    # Network tools: ping, jitter, loss
    NETWORK = "netool.cgi"


class EndpointNoCheck(str, Enum):
    """Endpoints that should not be checked for availability."""

    # AURA control / RGB
    AURA = "set_ledg.cgi"


# Typehint for the endpoint
EndpointType = Endpoint | EndpointControl | EndpointService | EndpointTools


# Force request type for the endpoint
ENDPOINT_FORCE_REQUEST = {
    Endpoint.PORT_STATUS: RequestType.GET,
    EndpointTools.NETWORK: RequestType.GET,
}


SENSITIVE_ENDPOINTS: Final[frozenset[EndpointType]] = frozenset(
    {
        EndpointService.LOGIN,
        EndpointControl.APPLY,
    }
)


def is_sensitive_endpoint(endpoint: EndpointType) -> bool:
    """Check if the endpoint is sensitive."""

    return endpoint in SENSITIVE_ENDPOINTS


def _get_module(
    endpoint: Endpoint | EndpointControl | EndpointTools,
) -> ModuleType | None:
    """Attempt to get the module for the endpoint."""

    try:
        # Get the module name from the endpoint
        module_name = f"asusrouter.modules.endpoint.{endpoint.name.lower()}"

        # Import the module in a separate thread
        # to avoid blocking the main thread
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(importlib.import_module, module_name)
            # Return the module
            return future.result()

    except ModuleNotFoundError:
        _LOGGER.debug("No module found for endpoint %s", endpoint)
        return None


def read(
    endpoint: Endpoint | EndpointControl | EndpointTools,
    content: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Read the data from an endpoint."""

    _LOGGER.debug("Reading data from endpoint %s", endpoint)

    # Get the module
    submodule = _get_module(endpoint)

    # Read the data if module found
    if submodule:
        result = submodule.read(content, **kwargs)
        if isinstance(result, dict):
            return result
        return {}

    return {}


def process(
    endpoint: Endpoint,
    data: dict[str, Any],
    history: dict[AsusData, AsusDataState] | None = None,
    firmware: Firmware | None = None,
    wlan: list[Wlan] | None = None,
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
        result = submodule.process(data)
        if isinstance(result, dict):
            return result
        return {}

    return {}


def data_set(data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Append the data to the data dict."""

    # Update the data dict with kwargs using dictionary comprehension
    data.update(dict(kwargs.items()))

    # Return the data
    return data


def data_get(data: dict[str, Any], key: str) -> Any | None:
    """Extract value from the data dict and update the data dict."""

    # Get the value
    value = data.get(key)

    # Remove the value from the data dict
    data.pop(key, None)

    # Return the value
    return value


async def check_available(
    endpoint: Endpoint | EndpointTools,
    api_query: Callable[..., Awaitable[Any]],
) -> tuple[bool, Any | None]:
    """Check whether the endpoint is available or returns 404."""

    try:
        status, _, content = await api_query(endpoint)
        if status == HTTPStatus.OK:
            return (True, content)
    except AsusRouter404Error:
        return (False, None)

    return (False, None)
