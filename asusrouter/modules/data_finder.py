"""Data finder module."""

from __future__ import annotations

from collections.abc import Callable
import logging

from asusrouter.modules.data import AsusData
from asusrouter.modules.endpoint.hook_const import (
    MAP_OVPN_SERVER_388,
    MAP_VPNC_WIREGUARD,
    MAP_WIREGUARD_CLIENT,
    MAP_WIREGUARD_SERVER,
)
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.parental_control import HOOK_PC
from asusrouter.tools import converters

_LOGGER = logging.getLogger(__name__)


class AsusDataFinder:
    """AsusRouter data finder class."""

    def __init__(
        self,
        endpoint: list[AREndpoint] | AREndpoint,
        request: list[tuple[str, ...]] | None = None,
        nvram: list[str] | str | None = None,
        method: Callable | None = None,
    ) -> None:
        """Initialize the data finder."""

        # Set the endpoint as list even if it's a single endpoint
        if not isinstance(endpoint, list):
            endpoint = [endpoint]
        self.endpoint = endpoint

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
    "vpnc": [
        ("get_vpnc_status", ""),
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
    "vpnc": [
        "vpnc_clientlist",
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
    AsusData.DDNS: AsusDataFinder(
        AREndpoint.FETCH_DATA,
        nvram=ASUSDATA_NVRAM["ddns"],
    ),
    AsusData.LED: AsusDataFinder(
        AREndpoint.FETCH_DATA, nvram=ASUSDATA_NVRAM["light"]
    ),
    AsusData.OPENVPN: AsusDataFinder(AREndpoint.FETCH_VPN_STATUS),
    AsusData.OPENVPN_CLIENT: AsusData.OPENVPN,
    AsusData.OPENVPN_SERVER: AsusData.OPENVPN,
    AsusData.PARENTAL_CONTROL: AsusDataFinder(
        AREndpoint.FETCH_DATA, nvram=ASUSDATA_NVRAM["parental_control"]
    ),
    AsusData.PORT_FORWARDING: AsusDataFinder(
        AREndpoint.FETCH_DATA, nvram=ASUSDATA_NVRAM["port_forwarding"]
    ),
    AsusData.VPNC: AsusDataFinder(
        AREndpoint.FETCH_DATA,
        nvram=ASUSDATA_NVRAM["vpnc"],
        request=ASUSDATA_REQUEST["vpnc"],
    ),
    AsusData.VPNC_CLIENTLIST: AsusData.VPNC,
    AsusData.WIREGUARD: AsusData.WIREGUARD_SERVER,
    AsusData.WIREGUARD_CLIENT: AsusData.VPNC,
    AsusData.WIREGUARD_SERVER: AsusDataFinder(
        AREndpoint.FETCH_DATA,
        nvram=ASUSDATA_NVRAM["wireguard_server"],
        request=ASUSDATA_REQUEST["wireguard_server"],
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
