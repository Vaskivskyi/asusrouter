"""Data finder module."""

from __future__ import annotations

from enum import Enum
from typing import Callable, Optional

from asusrouter.modules.attributes import AsusRouterAttribute
from asusrouter.modules.data import AsusData
from asusrouter.modules.endpoint import Endpoint
from asusrouter.modules.parental_control import (
    KEY_PARENTAL_CONTROL_MAC,
    KEY_PARENTAL_CONTROL_NAME,
    KEY_PARENTAL_CONTROL_STATE,
    KEY_PARENTAL_CONTROL_TIMEMAP,
    KEY_PARENTAL_CONTROL_TYPE,
)
from asusrouter.modules.wlan import gwlan_nvram_request, wlan_nvram_request
from asusrouter.tools import converters


class AsusDataMerge(str, Enum):
    """AsusRouter data merge class."""

    ALL = "all"
    ANY = "any"


class AsusDataFinder:
    """AsusRouter data finder class."""

    def __init__(
        self,
        endpoint: list[Endpoint] | Endpoint,
        merge: AsusDataMerge = AsusDataMerge.ANY,
        request: Optional[list[tuple[str, ...]]] = None,
        nvram: Optional[list[str] | str] = None,
        method: Optional[Callable] = None,
        arguments: Optional[AsusRouterAttribute] = None,
    ) -> None:
        """Initialize the data finder."""

        # Set the endpoint as list even if it's a single endpoint
        if isinstance(endpoint, Endpoint):
            endpoint = [endpoint]
        self.endpoint = endpoint

        # Set the merge
        self.merge = merge

        # Set the request and append nvram hooks to the request
        self.request = request or []
        if nvram:
            nvram_request = converters.nvram_get(nvram)
            if nvram_request:
                self.request.extend(nvram_request)

        # Set the method and arguments
        self.method = method
        self.arguments = arguments


# A constant list of requests for fetching data
ASUSDATA_REQUEST = {
    "devices": {
        ("get_clientlist", ""),
    },
    "main": {
        ("cpu_usage", "appobj"),
        ("memory_usage", "appobj"),
        ("netdev", "appobj"),
        ("wanlink_state", "appobj"),
    },
}

ASUSDATA_NVRAM = {
    "light": ["led_val"],
    "parental_control": [
        KEY_PARENTAL_CONTROL_MAC,
        KEY_PARENTAL_CONTROL_NAME,
        KEY_PARENTAL_CONTROL_STATE,
        KEY_PARENTAL_CONTROL_TIMEMAP,
        KEY_PARENTAL_CONTROL_TYPE,
    ],
    "port_forwarding": [
        "vts_rulelist",
        "vts_enable_x",
    ],
}

ASUSDATA_ENDPOINT_APPEND = {
    Endpoint.PORT_STATUS: {
        "node_mac": AsusRouterAttribute.MAC,
    }
}


# A map of endptoins to get data from
ASUSDATA_MAP = {
    AsusData.AIMESH: AsusDataFinder(Endpoint.ONBOARDING),
    AsusData.BOOTTIME: AsusDataFinder(Endpoint.DEVICEMAP),
    AsusData.CLIENTS: AsusDataFinder(
        [Endpoint.ONBOARDING, Endpoint.UPDATE_CLIENTS], AsusDataMerge.ALL
    ),
    AsusData.CPU: AsusDataFinder(Endpoint.HOOK, request=ASUSDATA_REQUEST["main"]),
    AsusData.DEVICEMAP: AsusDataFinder(Endpoint.DEVICEMAP),
    AsusData.FIRMWARE: AsusDataFinder(Endpoint.FIRMWARE),
    AsusData.GWLAN: AsusDataFinder(
        Endpoint.HOOK,
        method=gwlan_nvram_request,
        arguments=AsusRouterAttribute.WLAN_LIST,
    ),
    AsusData.LED: AsusDataFinder(Endpoint.HOOK, nvram=ASUSDATA_NVRAM["light"]),
    AsusData.NETWORK: AsusDataFinder(Endpoint.HOOK, request=ASUSDATA_REQUEST["main"]),
    AsusData.NODE_INFO: AsusDataFinder(Endpoint.PORT_STATUS),
    AsusData.OPENVPN: AsusDataFinder(
        [Endpoint.VPN, Endpoint.DEVICEMAP], AsusDataMerge.ANY
    ),
    AsusData.PARENTAL_CONTROL: AsusDataFinder(
        Endpoint.HOOK, nvram=ASUSDATA_NVRAM["parental_control"]
    ),
    AsusData.PORT_FORWARDING: AsusDataFinder(
        Endpoint.HOOK, nvram=ASUSDATA_NVRAM["port_forwarding"]
    ),
    AsusData.PORTS: AsusDataFinder([Endpoint.PORT_STATUS, Endpoint.ETHERNET_PORTS]),
    AsusData.RAM: AsusDataFinder(Endpoint.HOOK, request=ASUSDATA_REQUEST["main"]),
    AsusData.SYSINFO: AsusDataFinder(Endpoint.SYSINFO),
    AsusData.TEMPERATURE: AsusDataFinder(Endpoint.TEMPERATURE),
    AsusData.WAN: AsusDataFinder(Endpoint.HOOK, request=ASUSDATA_REQUEST["main"]),
    AsusData.WLAN: AsusDataFinder(
        Endpoint.HOOK,
        method=wlan_nvram_request,
        arguments=AsusRouterAttribute.WLAN_LIST,
    ),
}
