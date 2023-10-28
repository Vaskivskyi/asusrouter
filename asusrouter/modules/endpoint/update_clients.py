"""Update Clients endpoint module."""

from __future__ import annotations

import re
from typing import Any

from asusrouter.modules.data import AsusData
from asusrouter.tools.cleaners import clean_dict, clean_dict_key
from asusrouter.tools.readers import merge_dicts, read_json_content, readable_mac


def read(content: str) -> dict[str, Any]:
    """Read update clients data"""

    update_clients: dict[str, Any] = {}

    # Our JSON data is between `originData =` and `networkmap_fullscan = `
    regex = re.compile(r"originData = (.*)networkmap_fullscan = ")
    match = regex.search(content.replace("\n", ""))
    if match:
        content = (
            match.group(1)
            .replace("fromNetworkmapd", '"fromNetworkmapd"')
            .replace("nmpClient :", '"nmpClient" :')
        )

        # Read the json content
        update_clients = read_json_content(content)

    return update_clients


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
