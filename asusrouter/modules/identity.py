"""Identity module.

This module contains all the classes and method to handle the identity of an Asus device."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from itertools import chain
from typing import Any, Awaitable, Callable, Optional, Tuple

from asusrouter.error import AsusRouterIdentityError
from asusrouter.modules.aimesh import AiMeshDevice
from asusrouter.modules.color import color_zone
from asusrouter.modules.data import AsusData
from asusrouter.modules.endpoint import (
    Endpoint,
    EndpointNoCheck,
    EndpointTools,
    EndpointType,
    check_available,
)
from asusrouter.modules.endpoint.onboarding import (
    process as process_onboarding,
)
from asusrouter.modules.endpoint.onboarding import read as read_onboarding
from asusrouter.modules.firmware import Firmware
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
    ("productid", "product_id"),
    ("productid", "model"),
    ("firmver", "fw_major"),
    ("buildno", "fw_minor"),
    ("extendno", "fw_build"),
    ("rc_support", "services", safe_list_from_string),
    ("ss_support", "services", safe_list_from_string),
    ("led_val", "led", safe_exists),
    ("ledg_rgb1", "aura", safe_exists),
    ("ledg_rgb2", "aura_zone", color_zone),
)


@dataclass
class AsusDevice:  # pylint: disable=too-many-instance-attributes
    """Asus device class.

    This class contains information about an Asus device
    and can represent a router, AiMesh nore or range extender."""

    # Device-defining values
    serial: Optional[str] = None
    mac: Optional[str] = None
    product_id: Optional[str] = None
    model: Optional[str] = None
    brand: str = "ASUSTek"

    # Supported features
    aimesh: bool = False

    # Device information
    firmware: Optional[Firmware] = None
    merlin: bool = False
    wlan: Optional[list[Wlan]] = None
    endpoints: Optional[dict[EndpointType, bool]] = None
    services: Optional[list[str]] = None

    # Flags for device features
    aura: bool = False
    aura_zone: int = 0
    led: bool = False
    ookla: bool = False
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
        raise AsusRouterIdentityError(
            "Failed to collect identity data from the router"
        ) from ex
    _LOGGER.debug("Identity collected")

    # Read the identity
    identity = _read_nvram(identity_map)
    _LOGGER.debug("Identity read")

    # Process services
    identity["aimesh"] = "amas" in identity["services"]

    # Check endpoints
    endpoints, onboarding = await _check_endpoints(api_query)
    identity["endpoints"] = endpoints
    _LOGGER.debug("Endpoints checked")
    # Manually assign Aura endpoint value
    identity["endpoints"][EndpointTools.AURA] = identity.get("aura", False)

    # Check onboarding to get nice model name
    this_device = onboarding.get(identity["mac"])
    if isinstance(this_device, AiMeshDevice):
        identity["model"] = this_device.model

    # Check if Merlin
    if endpoints[Endpoint.SYSINFO] is True:
        identity["merlin"] = True
        _LOGGER.debug("Merlin FW detected")

    # Return the identity convered from a dict
    return AsusDevice(**identity)


# UPDATE THIS METHOD
def _read_nvram(data: dict[str, Any]) -> dict[str, Any]:
    """Read the NVRAM identity data."""

    # Check the input data
    if not data:
        raise AsusRouterIdentityError("No nvram data received")

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
    firmware = Firmware(
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

    # OOKLA Speedtest
    if "ookla" in identity["services"]:
        identity["ookla"] = True

    return identity


async def _check_endpoints(
    api_hook: Callable[..., Awaitable[Any]],
) -> tuple[dict[EndpointType, bool], dict[str, Any]]:
    """Check which endpoints are available."""

    endpoints: dict[EndpointType, bool] = {}
    contents: dict[EndpointType, Any] = {}

    for endpoint in chain(Endpoint, EndpointTools):
        if endpoint.name in EndpointNoCheck.__members__:
            continue
        result, content = await check_available(endpoint, api_hook)
        endpoints[endpoint] = result
        contents[endpoint] = content

    onboarding = {}
    if endpoints[Endpoint.ONBOARDING] is True:
        onboarding = process_onboarding(
            read_onboarding(contents[Endpoint.ONBOARDING])
        ).get(AsusData.AIMESH, {})

    return (endpoints, onboarding)
