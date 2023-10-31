"""Identity module.

This module contains all the classes and method to handle the identity of an Asus device."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Tuple

from asusrouter.error import AsusRouterIdentityError
from asusrouter.modules.endpoint import Endpoint, check_available
from asusrouter.modules.firmware import Firmware, read_fw_string
from asusrouter.modules.wlan import WLAN_TYPE, Wlan
from asusrouter.tools import writers
from asusrouter.tools.cleaners import clean_dict
from asusrouter.tools.converters import (
    safe_exists,
    safe_list_from_string,
    safe_unpack_keys,
)

_LOGGER = logging.getLogger(__name__)

MAP_IDENTITY: Tuple = (
    ("serial_no", "serial"),
    ("label_mac", "mac"),
    ("lan_hwaddr", "lan_mac"),
    ("wan_hwaddr", "wan_mac"),
    ("productid", "model"),
    ("firmver", "fw_major"),
    ("buildno", "fw_minor"),
    ("extendno", "fw_build"),
    ("rc_support", "services", safe_list_from_string),
    ("ss_support", "services", safe_list_from_string),
    ("led_val", "led", safe_exists),
)


@dataclass
class AsusDevice:  # pylint: disable=too-many-instance-attributes
    """Asus device class.

    This class contains information about an Asus device
    and can represent a router, AiMesh nore or range extender."""

    # Device-defining values
    serial: Optional[str] = None
    mac: Optional[str] = None
    model: Optional[str] = None
    brand: str = "ASUSTek"

    # Device information
    firmware: Optional[Firmware] = None
    wlan: Optional[list[Wlan]] = None
    endpoints: Optional[dict[Endpoint, bool]] = None
    services: Optional[list[str]] = None

    # Flags for device features
    led: bool = False
    ledg: bool = False
    aura: bool = False
    vpn_status: bool = False


async def collect_identity(
    api_hook: Callable[..., Awaitable[dict[str, Any]]],
    api_query: Callable[..., Awaitable[Any]],
) -> AsusDevice:
    """Collect device identity."""

    _LOGGER.debug("Collecting device identity")

    # Prepare a request
    request_values = []
    for map_item in MAP_IDENTITY:
        key, _, _ = safe_unpack_keys(map_item)
        request_values.append(key)
    request = writers.nvram(request_values)

    # Get the identity data
    try:
        identity_map = await api_hook(request)
    except Exception as ex:  # pylint: disable=broad-except
        raise AsusRouterIdentityError from ex
    _LOGGER.debug("Identity collected")

    # Read the identity
    identity = _read_nvram(identity_map)
    _LOGGER.debug("Identity read")

    # Check endpoints
    endpoints = await _check_endpoints(api_query)
    identity["endpoints"] = endpoints
    _LOGGER.debug("Endpoints checked")

    # TODO: Remove legacy
    # Mark endpoint for FW 380
    if identity["firmware"].minor == 380:
        identity["endpoint_devices"] = "devices"
        _LOGGER.debug("Legacy endpoint marked")

    # Return the identity convered from a dict
    return AsusDevice(**identity)


# UPDATE THIS METHOD
def _read_nvram(data: dict[str, Any]) -> dict[str, Any]:
    """Read the NVRAM identity data."""

    # Check the input data
    if not data:
        raise AsusRouterIdentityError("No data received")

    # Create the identity dictionary
    identity: dict[str, Any] = {}

    # Loop through the identity map
    for map_item in MAP_IDENTITY:
        key, key_to_use, method = safe_unpack_keys(map_item)
        try:
            value = method(data[key]) if method else data[key]
            if key_to_use in identity:
                if isinstance(identity[key_to_use], list):
                    identity[key_to_use].extend(value)
                else:
                    identity[key_to_use] = value
            else:
                identity[key_to_use] = value
        except Exception as ex:
            raise ex

    # Clean up the identity dictionary
    identity = clean_dict(identity)

    # MAC (for some Merlin firmwares missing label_mac)
    if not identity.get("mac"):
        if identity.get("lan_mac"):
            identity["mac"] = identity["lan_mac"]
        elif identity.get("wan_mac"):
            identity["mac"] = identity["wan_mac"]
    # Remove extra MACs
    identity.pop("lan_mac")
    identity.pop("wan_mac")

    # Firmware
    # TODO: Optimize this
    firmware = read_fw_string(
        f"{identity['fw_major']}.{identity['fw_minor']}.{identity['fw_build']}"
    )
    identity["firmware"] = firmware
    identity.pop("fw_major")
    identity.pop("fw_minor")
    identity.pop("fw_build")

    # WLAN list
    identity["wlan"] = []
    for value in identity["services"]:
        if value in WLAN_TYPE:
            identity["wlan"].append(WLAN_TYPE[value])

    return identity


async def _check_endpoints(
    api_hook: Callable[..., Awaitable[Any]]
) -> dict[Endpoint, bool]:
    """Check which endpoints are available."""

    endpoints: dict[Endpoint, bool] = {}

    for endpoint in Endpoint:
        endpoints[endpoint] = await check_available(endpoint, api_hook)

    return endpoints
