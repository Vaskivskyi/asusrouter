"""Data finder module."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Callable, Optional

from asusrouter.modules.attributes import AsusRouterAttribute
from asusrouter.modules.data import AsusData
from asusrouter.modules.endpoint import Endpoint, EndpointTools, EndpointType
from asusrouter.modules.endpoint.hook_const import (
    MAP_OVPN_SERVER_388,
    MAP_VPNC_WIREGUARD,
    MAP_WAN,
    MAP_WAN_ITEM,
    MAP_WAN_ITEM_X,
    MAP_WIREGUARD_CLIENT,
    MAP_WIREGUARD_SERVER,
)
from asusrouter.modules.parental_control import HOOK_PC
from asusrouter.modules.wlan import gwlan_nvram_request, wlan_nvram_request
from asusrouter.tools import converters

_LOGGER = logging.getLogger(__name__)


class AsusDataMerge(str, Enum):
    """AsusRouter data merge class."""

    ALL = "all"
    ANY = "any"


class AsusDataFinder:
    """AsusRouter data finder class."""

    def __init__(
        self,
        endpoint: list[EndpointType] | EndpointType,
        merge: AsusDataMerge = AsusDataMerge.ANY,
        request: Optional[list[tuple[str, ...]]] = None,
        nvram: Optional[list[str] | str] = None,
        method: Optional[Callable] = None,
        arguments: Optional[AsusRouterAttribute] = None,
    ) -> None:
        """Initialize the data finder."""

        # Set the endpoint as list even if it's a single endpoint
        if not isinstance(endpoint, list):
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
    "devices": [
        ("get_clientlist", ""),
    ],
    "main": [
        ("cpu_usage", "appobj"),
        ("memory_usage", "appobj"),
        ("netdev", "appobj"),
    ],
    "speedtest": [
        ("ookla_speedtest_get_result", ""),
    ],
    # "speedtest_history": [
    #     ("ookla_speedtest_get_history", ""),
    # ],
    # "speedtest_servers": [
    #     ("ookla_speedtest_get_servers", ""),
    # ],
    "vpnc": [
        ("get_vpnc_status", ""),
    ],
    "wan": [
        ("get_wan_unit", ""),
    ],
    "wireguard_server": [
        ("get_wgsc_status", ""),
    ],
}

ASUSDATA_NVRAM = {
    "aura": [
        "AllLED",
        "ledg_night_mode",
        "ledg_scheme",
        "ledg_scheme_old",
    ],
    "light": ["led_val"],
    "openvpn_server_388": [
        key
        for element in MAP_OVPN_SERVER_388
        for key, _, _ in [converters.safe_unpack_keys(element)]
    ],
    "parental_control": HOOK_PC,
    "port_forwarding": [
        "vts_rulelist",
        "vts_enable_x",
    ],
    "speedtest": ["ookla_state"],
    "vpnc": [
        "vpnc_clientlist",
    ],
    "wan": [
        key
        for element in MAP_WAN
        for key, _, _ in [converters.safe_unpack_keys(element)]
        if key != "get_wan_unit"
    ],
    "wireguard_server": [
        key
        for element in MAP_WIREGUARD_SERVER
        for key, _, _ in [converters.safe_unpack_keys(element)]
        if key != "get_wgsc_status"
    ],
}
ASUSDATA_NVRAM["aura"].extend([f"ledg_rgb{num}" for num in range(0, 8)])
ASUSDATA_NVRAM["vpnc"].extend(
    [
        f"wgc{num}_{key}"
        for num in range(1, 6)
        for element in MAP_VPNC_WIREGUARD
        for key, _, _ in [converters.safe_unpack_keys(element)]
    ]
)
ASUSDATA_NVRAM["wan"].extend(
    [
        f"wan{num}_{key}"
        for num in (0, 1)
        for element in MAP_WAN_ITEM
        for key, _, _ in [converters.safe_unpack_keys(element)]
    ]
)
ASUSDATA_NVRAM["wan"].extend(
    [
        f"wan{num}_{extra}{key}"
        for num in (0, 1)
        for extra in ("", "x")
        for element in MAP_WAN_ITEM_X
        for key, _, _ in [converters.safe_unpack_keys(element)]
    ]
)
ASUSDATA_NVRAM["wireguard_server"].extend(
    [
        f"wgs1_c{num}_{key}"
        for num in range(1, 11)
        for element in MAP_WIREGUARD_CLIENT
        for key, _, _ in [converters.safe_unpack_keys(element)]
    ]
)

ASUSDATA_ENDPOINT_APPEND = {
    Endpoint.PORT_STATUS: {
        # Request status of the ports for the whole AiMesh network
        # This will save time and requests, since we then cache the data
        # in most cases
        "node_mac": "all",
    }
}


# A map of endptoins to get data from
ASUSDATA_MAP: dict[AsusData, AsusData | AsusDataFinder] = {
    AsusData.AIMESH: AsusDataFinder(Endpoint.ONBOARDING),
    AsusData.AURA: AsusDataFinder(
        Endpoint.HOOK,
        nvram=ASUSDATA_NVRAM["aura"],
    ),
    AsusData.BOOTTIME: AsusData.DEVICEMAP,
    AsusData.CLIENTS: AsusDataFinder(
        [Endpoint.ONBOARDING, Endpoint.UPDATE_CLIENTS], AsusDataMerge.ALL
    ),
    AsusData.CPU: AsusDataFinder(
        Endpoint.HOOK, request=ASUSDATA_REQUEST["main"]
    ),
    AsusData.DEVICEMAP: AsusDataFinder(Endpoint.DEVICEMAP),
    AsusData.FIRMWARE: AsusDataFinder(Endpoint.FIRMWARE),
    AsusData.FIRMWARE_NOTE: AsusDataFinder(
        [Endpoint.FIRMWARE_NOTE, Endpoint.FIRMWARE_NOTE_AIMESH]
    ),
    AsusData.GWLAN: AsusDataFinder(
        Endpoint.HOOK,
        method=gwlan_nvram_request,
        arguments=AsusRouterAttribute.WLAN_LIST,
    ),
    AsusData.LED: AsusDataFinder(Endpoint.HOOK, nvram=ASUSDATA_NVRAM["light"]),
    AsusData.NETWORK: AsusData.CPU,
    AsusData.NODE_INFO: AsusDataFinder(Endpoint.PORT_STATUS),
    AsusData.OPENVPN: AsusDataFinder(
        [Endpoint.VPN, Endpoint.DEVICEMAP], AsusDataMerge.ANY
    ),
    AsusData.OPENVPN_CLIENT: AsusData.OPENVPN,
    AsusData.OPENVPN_SERVER: AsusData.OPENVPN,
    AsusData.PARENTAL_CONTROL: AsusDataFinder(
        Endpoint.HOOK, nvram=ASUSDATA_NVRAM["parental_control"]
    ),
    AsusData.PING: AsusDataFinder(EndpointTools.NETWORK),
    AsusData.PORT_FORWARDING: AsusDataFinder(
        Endpoint.HOOK, nvram=ASUSDATA_NVRAM["port_forwarding"]
    ),
    AsusData.PORTS: AsusDataFinder(
        [Endpoint.PORT_STATUS, Endpoint.ETHERNET_PORTS]
    ),
    AsusData.RAM: AsusData.CPU,
    AsusData.SPEEDTEST: AsusDataFinder(
        Endpoint.HOOK,
        nvram=ASUSDATA_NVRAM["speedtest"],
        request=ASUSDATA_REQUEST["speedtest"],
    ),
    # AsusData.SPEEDTEST_HISTORY: AsusDataFinder(
    #     Endpoint.HOOK, request=ASUSDATA_REQUEST["speedtest_history"]
    # ),
    AsusData.SPEEDTEST_RESULT: AsusData.SPEEDTEST,
    # AsusData.SPEEDTEST_SERVERS: AsusDataFinder(
    #     Endpoint.HOOK, request=ASUSDATA_REQUEST["speedtest_servers"]
    # ),
    AsusData.SYSINFO: AsusDataFinder(Endpoint.SYSINFO),
    AsusData.TEMPERATURE: AsusDataFinder(Endpoint.TEMPERATURE),
    AsusData.VPNC: AsusDataFinder(
        Endpoint.HOOK,
        nvram=ASUSDATA_NVRAM["vpnc"],
        request=ASUSDATA_REQUEST["vpnc"],
    ),
    AsusData.VPNC_CLIENTLIST: AsusData.VPNC,
    AsusData.WAN: AsusDataFinder(
        Endpoint.HOOK,
        nvram=ASUSDATA_NVRAM["wan"],
        request=ASUSDATA_REQUEST["wan"],
    ),
    AsusData.WIREGUARD: AsusData.WIREGUARD_SERVER,
    AsusData.WIREGUARD_CLIENT: AsusData.VPNC,
    AsusData.WIREGUARD_SERVER: AsusDataFinder(
        Endpoint.HOOK,
        nvram=ASUSDATA_NVRAM["wireguard_server"],
        request=ASUSDATA_REQUEST["wireguard_server"],
    ),
    AsusData.WLAN: AsusDataFinder(
        Endpoint.HOOK,
        method=wlan_nvram_request,
        arguments=AsusRouterAttribute.WLAN_LIST,
    ),
}


def add_conditional_data_rule(data: AsusData, rule: AsusDataFinder) -> None:
    """A callback to add / change rule for ASUSDATA_MAP."""

    ASUSDATA_MAP[data] = rule
    _LOGGER.debug("Added conditional data rule: %s -> %s", data, rule)


def add_conditional_data_alias(data: AsusData, origin: AsusData) -> None:
    """A callback to add / change rule for ASUSDATA_MAP."""

    ASUSDATA_MAP[data] = origin
    _LOGGER.debug("Added data alias: %s -> %s", origin, data)


def remove_data_rule(data: AsusData) -> None:
    """A callback to remove rule for ASUSDATA_MAP."""

    ASUSDATA_MAP.pop(data, None)
    _LOGGER.debug("Removed data rule: %s", data)
