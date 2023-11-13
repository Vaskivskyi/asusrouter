"""VPN endpoint module."""

from __future__ import annotations

import re
from typing import Any

from asusrouter.modules.data import AsusData
from asusrouter.modules.openvpn import AsusOVPNClient, AsusOVPNServer
from asusrouter.tools.cleaners import clean_content
from asusrouter.tools.converters import safe_int
from asusrouter.tools.readers import read_as_snake_case, read_js_variables

from .vpn_const import MAP_OVPN_CLIENT, MAP_OVPN_SERVER

_TO_IGNORE = ("", "None", "0.0.0.0")


def read(content: str) -> dict[str, Any]:
    """Read VPN data."""

    vpn: dict[str, Any] = {
        "client": {},
        "server": {},
    }

    # Read the js variables
    values: dict[str, Any] = read_js_variables(clean_content(content))

    # Values to ignore

    # Read the OpenVPN data
    for party in ("client", "server"):
        # Select proper method and state
        method = read_ovpn_client if party == "client" else read_ovpn_server
        state = AsusOVPNClient if party == "client" else AsusOVPNServer

        for num in range(1, 11):
            key = f"vpn_{party}{num}_status"
            if key not in values:
                break

            # Read the data
            if values[key] not in _TO_IGNORE:
                vpn[party][num] = method(values[key])
                vpn[party][num]["state"] = state.CONNECTED
            else:
                vpn[party][num] = {"state": state.DISCONNECTED}

            # Read additional data
            for add_key in ("ip", "rip"):
                search_value = values.get(f"vpn_{party}{num}_{add_key}")
                if search_value and search_value not in _TO_IGNORE:
                    vpn[party][num][add_key] = search_value

            # Read remote
            search_value = vpn[party][num].get("remote")
            if search_value:
                vpn[party][num]["remote"] = read_ovpn_remote(search_value)

    return vpn


def read_ovpn_client(content: str) -> dict[str, Any]:
    """Read OpenVPN client data."""

    ovpn_client: dict[str, Any] = {}

    # Strip the content and make sure it's not an empty string
    content = content.strip()
    if content in ("", "None"):
        return ovpn_client

    # --------------------
    # THIS PART IS LEGACY AND CAN BE REMOVED IN THE FUTURE -->
    # --------------------

    for value in MAP_OVPN_CLIENT:
        key_old, key_new, method = value
        value = re.search(f"{key_old},(.*?)(?=>)", content)
        if value:
            ovpn_client[key_new] = method(value[1]) if method else value[1]

    # --------------------
    # <-- THIS PART IS LEGACY AND CAN BE REMOVED IN THE FUTURE
    # --------------------

    return ovpn_client


def read_ovpn_remote(content: str) -> dict[str, Any]:
    """Read OpenVPN remote data."""

    try:
        parts = content.split(",")
        auth = parts[1]
        parts = parts[0].split(":")
        ip_address = parts[0]
        port = safe_int(parts[1])
    except IndexError:
        return {}

    return {
        "ip": ip_address,
        "port": port,
        "auth": auth,
    }


def read_ovpn_server(content: str) -> dict[str, Any]:
    """Read OpenVPN server data."""

    ovpn_server: dict[str, Any] = {}

    # Strip the content and make sure it's not an empty string
    content = content.strip()
    if content in ("", "None"):
        return ovpn_server

    # --------------------
    # THIS PART IS LEGACY AND CAN BE REMOVED IN THE FUTURE -->
    # --------------------

    # Map the values
    for value in MAP_OVPN_SERVER:
        key_old, key_new = value
        if key_old in content:
            flag = False
            keys = []
            # Find headers
            header = re.search(f"HEADER,{key_old},(.*?)(?=>)", content)
            if header:
                keys_raw = header[1].split(",")
                for element in keys_raw:
                    keys.append(read_as_snake_case(element))
                flag = True

            # Hide header
            content = content.replace(f"HEADER,{key_old},", "USED-")

            ovpn_server[key_new] = []
            # Find values
            while value := re.search(f"{key_old},(.*?)(?=>)", content):
                if not value:
                    break
                if flag:
                    cut = value[1].split(",")
                    array = {k: v for k, v in zip(keys, cut)}
                    ovpn_server[key_new].append(array)
                else:
                    ovpn_server[key_new].append(value[1])
                content = content.replace(f"{key_old},{value[1]}", "USED-")
    # --------------------
    # <-- THIS PART IS LEGACY AND CAN BE REMOVED IN THE FUTURE
    # --------------------

    return ovpn_server


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process VPN data."""

    vpn: dict[AsusData, Any] = {
        AsusData.OPENVPN_CLIENT: data.get("client"),
        AsusData.OPENVPN_SERVER: data.get("server"),
    }

    return vpn
