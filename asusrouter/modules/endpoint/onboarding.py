"""Onboarding endpoint module."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.data import AsusData
from asusrouter.tools.converters_v2.raw import raw_to_int, raw_to_str
from asusrouter.tools.readers import read_js_variables

read = read_js_variables

CONNECTION_TYPE = {
    "2G": 1,
    "5G": 2,
    "5G1": 3,
    "5G2": 3,
    "6G": 4,
}


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process the onboarding data."""

    state: dict[AsusData, Any] = {}

    # Client list
    clients = {}
    client_list = data.get("get_allclientlist", [{}])[0]
    for node in client_list:
        for connection in client_list[node]:
            convert = process_connection(connection)
            for mac in client_list[node][connection]:
                description = {
                    "connection_type": convert.get("connection_type"),
                    "guest": convert.get("guest"),
                    "ip": raw_to_str(
                        client_list[node][connection][mac].get("ip", None)
                    ),
                    "mac": mac,
                    "node": node,
                    "online": True,
                    "rssi": client_list[node][connection][mac].get(
                        "rssi", None
                    ),
                }
                clients[mac] = description

    state[AsusData.CLIENTS] = clients

    return state


def process_connection(data: str) -> dict[str, int]:
    """Process connection data."""

    # Check that the data is not empty
    if not isinstance(data, str) or data == "":
        return {}

    if data == "wired_mac":
        return {"connection_type": 0, "guest": 0}

    temp = data.split("_")
    return {
        "connection_type": CONNECTION_TYPE.get(temp[0]) or 0,
        "guest": (raw_to_int(temp[1]) or 0) if len(temp) > 1 else 0,
    }
