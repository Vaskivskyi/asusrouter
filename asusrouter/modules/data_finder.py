"""Data finder module."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
import logging

from asusrouter.modules.data import AsusData
from asusrouter.modules.endpoint.hook_const import (
    MAP_OVPN_SERVER_388,
    MAP_VPNC_WIREGUARD,
    MAP_WAN,
    MAP_WAN_ITEM,
    MAP_WAN_ITEM_X,
    MAP_WIREGUARD_CLIENT,
    MAP_WIREGUARD_SERVER,
)
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.parental_control import HOOK_PC
from asusrouter.modules.wlan import gwlan_nvram_request, wlan_nvram_request
from asusrouter.tools import converters

_LOGGER = logging.getLogger(__name__)


class AsusDataMerge(StrEnum):
    """AsusRouter data merge class."""

    ALL = "all"
    ANY = "any"


class AsusDataFinder:
    """AsusRouter data finder class."""

    def __init__(  # noqa: PLR0913
        self,
        endpoint: list[AREndpoint] | AREndpoint,
        merge: AsusDataMerge = AsusDataMerge.ANY,
        request: list[tuple[str, ...]] | None = None,
        nvram: list[str] | str | None = None,
        method: Callable | None = None,
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

        self.method = method


# A constant list of requests for fetching data
ASUSDATA_REQUEST = {
    "devices": [
        ("get_clientlist", ""),
    ],
    "network": [
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
    "ddns": [
        "ddns_enable_x",
        "ddns_hostname_x",
        "ddns_ipaddr",
        "ddns_old_name",
        "ddns_replace_status",
        "ddns_return_code",
        "ddns_return_code_chk",
        "ddns_server_x",
        "ddns_updated",
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
    "dsl": [
        "dsllog_dataratedown",
        "dsllog_datarateup",
    ],
}
ASUSDATA_NVRAM["aura"].extend([f"ledg_rgb{num}" for num in range(8)])
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

# A map of endptoins to get data from
ASUSDATA_MAP: dict[AsusData, AsusData | AsusDataFinder] = {
    AsusData.AURA: AsusDataFinder(
        AREndpoint.FETCH_DATA,
        nvram=ASUSDATA_NVRAM["aura"],
    ),
    AsusData.BOOTTIME: AsusData.DEVICEMAP,
    AsusData.CLIENTS: AsusDataFinder(
        [AREndpoint.FETCH_ONBOARDING, AREndpoint.FETCH_CLIENTS_UPDATE],
        AsusDataMerge.ALL,
    ),
    AsusData.DDNS: AsusDataFinder(
        AREndpoint.FETCH_DATA,
        nvram=ASUSDATA_NVRAM["ddns"],
    ),
    AsusData.DEVICEMAP: AsusDataFinder(AREndpoint.FETCH_DEVICEMAP),
    AsusData.FIRMWARE: AsusDataFinder(AREndpoint.FETCH_FIRMWARE_UPDATE),
    AsusData.FIRMWARE_NOTE: AsusDataFinder(
        [
            AREndpoint.FETCH_FIRMWARE_UPDATE_NOTE,
            AREndpoint.FETCH_FIRMWARE_UPDATE_NOTE_AIMESH,
        ]
    ),
    AsusData.GWLAN: AsusDataFinder(
        AREndpoint.FETCH_DATA,
        method=gwlan_nvram_request,
    ),
    AsusData.LED: AsusDataFinder(
        AREndpoint.FETCH_DATA, nvram=ASUSDATA_NVRAM["light"]
    ),
    AsusData.NETWORK: AsusDataFinder(
        AREndpoint.FETCH_DATA, request=ASUSDATA_REQUEST["network"]
    ),
    AsusData.OPENVPN: AsusDataFinder(
        [AREndpoint.FETCH_VPN_STATUS, AREndpoint.FETCH_DEVICEMAP],
        AsusDataMerge.ANY,
    ),
    AsusData.OPENVPN_CLIENT: AsusData.OPENVPN,
    AsusData.OPENVPN_SERVER: AsusData.OPENVPN,
    AsusData.PARENTAL_CONTROL: AsusDataFinder(
        AREndpoint.FETCH_DATA, nvram=ASUSDATA_NVRAM["parental_control"]
    ),
    AsusData.PING: AsusDataFinder(AREndpoint.FETCH_NETWORK),
    AsusData.PORT_FORWARDING: AsusDataFinder(
        AREndpoint.FETCH_DATA, nvram=ASUSDATA_NVRAM["port_forwarding"]
    ),
    AsusData.SPEEDTEST: AsusDataFinder(
        AREndpoint.FETCH_DATA,
        nvram=ASUSDATA_NVRAM["speedtest"],
        request=ASUSDATA_REQUEST["speedtest"],
    ),
    # AsusData.SPEEDTEST_HISTORY: AsusDataFinder(
    #     AREndpoint.FETCH_DATA, request=ASUSDATA_REQUEST["speedtest_history"]
    # ),
    AsusData.SPEEDTEST_RESULT: AsusData.SPEEDTEST,
    # AsusData.SPEEDTEST_SERVERS: AsusDataFinder(
    #     AREndpoint.FETCH_DATA, request=ASUSDATA_REQUEST["speedtest_servers"]
    # ),
    AsusData.SYSINFO: AsusDataFinder(AREndpoint.FETCH_SYSINFO),
    AsusData.VPNC: AsusDataFinder(
        AREndpoint.FETCH_DATA,
        nvram=ASUSDATA_NVRAM["vpnc"],
        request=ASUSDATA_REQUEST["vpnc"],
    ),
    AsusData.VPNC_CLIENTLIST: AsusData.VPNC,
    AsusData.WAN: AsusDataFinder(
        AREndpoint.FETCH_DATA,
        nvram=ASUSDATA_NVRAM["wan"],
        request=ASUSDATA_REQUEST["wan"],
    ),
    AsusData.WIREGUARD: AsusData.WIREGUARD_SERVER,
    AsusData.WIREGUARD_CLIENT: AsusData.VPNC,
    AsusData.WIREGUARD_SERVER: AsusDataFinder(
        AREndpoint.FETCH_DATA,
        nvram=ASUSDATA_NVRAM["wireguard_server"],
        request=ASUSDATA_REQUEST["wireguard_server"],
    ),
    AsusData.WLAN: AsusDataFinder(
        AREndpoint.FETCH_DATA,
        method=wlan_nvram_request,
    ),
    AsusData.DSL: AsusDataFinder(
        AREndpoint.FETCH_DATA,
        nvram=ASUSDATA_NVRAM["dsl"],
    ),
}


def add_conditional_data_rule(data: AsusData, rule: AsusDataFinder) -> None:
    """Add or change rule for ASUSDATA_MAP."""

    ASUSDATA_MAP[data] = rule
    _LOGGER.debug("Added conditional data rule: %s -> %s", data, rule)


def add_conditional_data_alias(data: AsusData, origin: AsusData) -> None:
    """Add or change rule for ASUSDATA_MAP."""

    ASUSDATA_MAP[data] = origin
    _LOGGER.debug("Added data alias: %s -> %s", origin, data)


def remove_data_rule(data: AsusData) -> None:
    """Remove rule for ASUSDATA_MAP."""

    ASUSDATA_MAP.pop(data, None)
    _LOGGER.debug("Removed data rule: %s", data)
