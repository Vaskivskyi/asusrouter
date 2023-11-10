"""Update Clients endpoint module."""

from __future__ import annotations

import logging
import re
from json import JSONDecodeError
from typing import Any, Optional
from urllib import parse

from asusrouter.modules.data import AsusData
from asusrouter.tools.cleaners import clean_dict, clean_dict_key
from asusrouter.tools.readers import merge_dicts, read_json_content, readable_mac

_LOGGER = logging.getLogger(__name__)


LEGACY_WLAN: dict[str, int] = {
    "2g": 1,
    "5g": 2,
    "5g_2": 3,
}


def read(content: str) -> dict[str, Any]:
    """Read update clients data"""

    update_clients: dict[str, Any] = {}

    # Our JSON data is between `originData =` and `networkmap_fullscan = `
    regex = re.compile(r"originData = (.*)networkmap_fullscan = ")
    match = regex.search(content.replace("\n", ""))
    if match:
        # Old firmwares have a different format
        if "staticList" in match.group(1):
            _LOGGER.debug("Reading legacy update clients data")
            return read_legacy(match.group(1))
        # Modern firmware
        _LOGGER.debug("Reading modern update clients data")
        content = (
            match.group(1)
            .replace("fromNetworkmapd", '"fromNetworkmapd"')
            .replace("nmpClient :", '"nmpClient" :')
        )

        # Read the json content
        update_clients = read_json_content(content)

    return update_clients


def read_legacy(content: str) -> dict[str, Any]:
    """Read update clients data from legacy firmwares."""

    clients: dict[str, Any] = {}

    data = read_legacy_as_json(content)

    # Networkmap
    read_legacy_networmap(clients, data.get("fromNetworkmapd"))
    # Staticlist
    read_legacy_staticlist(clients, data.get("staticList"))
    # Wlan list
    read_legacy_wlan_list(clients, data)
    # Wlan info
    read_legacy_wlan_info(clients, data)
    # nmpClient
    read_legacy_nmpclient(clients, data.get("nmpClient"))

    # Just so that we don't need to process it anyhow special
    # This will be compatible with the new format
    return {"fromNetworkmapd": [clients]}


def read_legacy_as_json(content: str) -> dict[str, Any]:
    """Read update clients data from legacy firmwares as JSON."""

    # Step 0 - replace all `'` with `"`
    data = content.replace("'", '"')

    # Step 1 - remove all the replace and split statements
    to_replace = [
        '.replace(/&#62/g, ">")',
        '.replace(/&#60/g, "<")',
        '.split("<")',
        '.split(">")',
    ]
    for replace in to_replace:
        data = data.replace(replace, "")

    # Step 2 - remove the `decodeURIComponent` statements
    data = data.replace("decodeURIComponent(", "").replace(")", "")

    # Step 3 - Remove the `{}` in the beginning and end, also clean trailing and leading spaces
    data = data[1:-1].strip()

    # Step 4 - decode
    data = parse.unquote(data)

    # Step 5 - replace the keys by the regex
    # Find all `, [a-zA-Z0-9_]+:` where [a-zA-Z0-9_]+ is the key and add `"` around the key
    data = re.sub(r", ?([a-zA-Z0-9_]+):", r',"\1":', data)

    # Step 6 - replace `customList` with `"customList"`
    data = data.replace("customList", '"customList"')

    # Step 7 - find `"wlList_2g": \[[.*]\]` as well as `"wlList_5g": \[[.*]\]` and `"wlList_5g_2": \[[.*]\]`
    # and replace them with `"wlList_2g": {[.*]}` as well as `"wlList_5g": {[.*]}` and `"wlList_5g_2": {[.*]}`
    # Keep the content inside the brackets as is
    # Stop the regex search on the first occurence of the `]` so that we don't match the last `]`
    data = re.sub(r'"wlList_2g": \[([^\]]*)\]', r'"wlList_2g": {\1}', data, count=1)
    data = re.sub(r'"wlList_5g": \[([^\]]*)\]', r'"wlList_5g": {\1}', data, count=1)
    data = re.sub(r'"wlList_5g_2": \[([^\]]*)\]', r'"wlList_5g_2": {\1}', data, count=1)

    data = "{" + data + "}"
    try:
        return read_json_content(data)
    except JSONDecodeError:
        _LOGGER.debug("Failed to read legacy update clients data")
        return {}


def read_legacy_networmap(output: dict[str, Any], networkmap: Optional[str]) -> None:
    """Read legacy networkmap to the output dict."""

    if not networkmap:
        return

    client_list = networkmap.split("<")
    for client_line in client_list:
        if client_line == "":
            continue
        client = client_line.split(">")
        if len(client) < 4 or not readable_mac(client[3].upper()):
            continue
        mac = client[3].upper()
        output[mac] = {
            "mac": mac,
            "name": client[1] if len(client) > 1 else None,
            "ip": client[2] if len(client) > 2 else None,
            "ipMethod": "dhcp",
            "isWL": 0,
            "isOnline": 1,
        }


def read_legacy_nmpclient(output: dict[str, Any], nmp_client: Optional[str]) -> None:
    """Read legacy nmpclient to the output dict."""

    if not nmp_client:
        return

    client_list = nmp_client.split("<")
    for client_info in client_list:
        # Skip empty strings
        if client_info == "":
            continue
        # Split the string into a list by `>`
        client = client_info.split(">")
        # Check if client has enough elements
        if len(client) < 5:
            continue
        # 0 element is the MAC address written in lowercase and without `:`
        # We need to convert it to uppercase and add `:`
        mac = ":".join([client[0][i : i + 2].upper() for i in range(0, 12, 2)])
        client_type = client[4] if len(client) > 4 else None
        if mac in output:
            output[mac]["type"] = client_type
            continue
        output[mac] = {
            "mac": mac,
            "name": client[2] if len(client) > 2 else None,
            "type": client_type,
            "isOnline": 0,
        }


def read_legacy_staticlist(output: dict[str, Any], static_list: Optional[str]) -> None:
    """Read legacy staticlist to the output dict."""

    if not static_list:
        return

    client_list = static_list.split("<")
    for client_line in client_list:
        if client_line == "":
            continue
        client = client_line.split(">")
        mac = client[0].upper()
        if not readable_mac(mac):
            continue
        if mac in output:
            output[mac]["ipMethod"] = "static"
            continue
        output[mac] = {
            "mac": mac,
            "name": client[2] if len(client) > 2 else None,
            "ip": client[1] if len(client) > 1 else None,
            "ipMethod": "static",
            "isWL": 0,
            "isOnline": 0,
        }


def read_legacy_wlan_info(output: dict[str, Any], data: dict[str, Any]) -> None:
    """Read legacy wlan info to the output dict."""

    for wlan in LEGACY_WLAN:
        wlan_info = data.get(f"wlListInfo_{wlan}")
        if not wlan_info:
            continue

        for client in wlan_info:
            mac = client[0].upper()
            if not readable_mac(mac):
                continue
            curTx = client[1] if len(client) > 1 else None
            curRx = client[2] if len(client) > 2 else None
            wlConnectTime = client[3] if len(client) > 3 else None
            if mac in output:
                output[mac]["curTx"] = curTx
                output[mac]["curRx"] = curRx
                output[mac]["wlConnectTime"] = wlConnectTime
                continue
            output[mac] = {
                "mac": mac,
                "curTx": curTx,
                "curRx": curRx,
                "wlConnectTime": wlConnectTime,
            }


def read_legacy_wlan_list(output: dict[str, Any], data: dict[str, Any]) -> None:
    """Read legacy wlan list to the output dict."""

    for wlan, wid in LEGACY_WLAN.items():
        wlan_list = data.get(f"wlList_{wlan}")
        if not wlan_list:
            continue

        for mac, client in wlan_list.items():
            if not readable_mac(mac):
                continue
            rssi = client.get("rssi")
            if mac in output:
                output[mac]["isWL"] = wid
                output[mac]["rssi"] = rssi
                output[mac]["isOnline"] = 1
                continue
            output[mac] = {
                "mac": mac,
                "isWL": wid,
                "rssi": rssi,
                "isOnline": 1,
            }


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process the update clients data."""

    state: dict[AsusData, Any] = {}

    # Clients from Networkmapd
    clients = {
        mac: description
        for mac, description in data.get("fromNetworkmapd", [{}])[0].items()
        if readable_mac(mac)
    }

    # Clients from nmpClient
    clients_historic = {
        mac: description
        for mac, description in data.get("nmpClient", [{}])[0].items()
        if readable_mac(mac)
    }

    # Merge states
    clients = merge_dicts(clients, clients_historic)
    # Clean the clients
    clean_dict(clients)
    # Clean the clients from the `from` field
    clients = clean_dict_key(clients, "from")

    state[AsusData.CLIENTS] = clients

    return state
