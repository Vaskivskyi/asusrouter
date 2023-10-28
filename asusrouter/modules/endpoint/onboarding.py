"""Onboarding endpoint module."""


from __future__ import annotations

from typing import Any

from asusrouter.modules.aimesh import AiMeshDevice
from asusrouter.modules.data import AsusData
from asusrouter.tools.cleaners import clean_content
from asusrouter.tools.converters import safe_bool, safe_int, safe_none_or_str
from asusrouter.tools.readers import read_json_content

CONNECTION_TYPE = {
    "2G": 1,
    "5G": 2,
    "5G1": 3,
    "5G2": 3,
    "6G": 4,
}


def read(content: str) -> dict[str, Any]:
    """Read onboarding data"""

    # Prepare the content
    content = (
        clean_content(content)
        .replace(" = ", '":')
        .replace(";\n", ',"')
        .replace("[0]", "")
    )
    content = '{"' + content[:-3] + "}"

    # Read the json content
    onboarding: dict[str, Any] = read_json_content(content)

    return onboarding


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process the onboarding data."""

    state: dict[AsusData, Any] = {}

    # AiMesh nodes state
    state[AsusData.AIMESH] = {
        node.mac: node
        for device in data.get("get_cfg_clientlist", [[]])[0]
        for node in [process_aimesh_node(device)]
    }

    # Client list
    clients = {}
    client_list = data["get_allclientlist"][0]
    for node in client_list:
        for connection in client_list[node]:
            convert = process_connection(connection)
            for mac in client_list[node][connection]:
                description = {
                    "connection_type": convert["connection_type"],
                    "guest": convert["guest"],
                    "ip": safe_none_or_str(
                        client_list[node][connection][mac].get("ip", None)
                    ),
                    "mac": mac,
                    "node": node,
                    "online": True,
                    "rssi": client_list[node][connection][mac].get("rssi", None),
                }
                clients[mac] = description

    state[AsusData.CLIENTS] = clients

    return state


def process_aimesh_node(data: dict[str, Any]) -> AiMeshDevice:
    """Process AiMesh node data."""

    const_ap = {
        "2g": "2ghz",
        "5g": "5ghz",
        "5g1": "5ghz2",
        "6g": "6ghz",
        "dwb": "dwb",
    }

    const_freq = [
        "2g",
        "5g",
        "6g",
    ]

    ap = {}
    for el, value in const_ap.items():
        if f"ap{el}" in data and data[f"ap{el}"] is not str():
            ap[value] = data[f"ap{el}"]

    parent = {}
    for el in const_freq:
        if f"pap{el}" in data and data[f"pap{el}"] is not str():
            parent["connection"] = const_ap[el]
            parent["mac"] = data[f"pap{el}"]
            parent["rssi"] = safe_none_or_str(data.get(f"rssi{el}"))
            parent["ssid"] = safe_none_or_str(data.get(f"pap{el}_ssid"))

    level = safe_int(data.get("level", "0"))
    node_type = "router" if level == 0 else "node"

    return AiMeshDevice(
        status=safe_bool(data.get("online", 0)) or False,
        alias=data.get("alias", None),
        model=data.get("ui_model_name", data.get("model_name", None)),
        product_id=data.get("product_id"),
        ip=data.get("ip"),
        fw=data.get("fwver", None),
        fw_new=safe_none_or_str(data.get("newfwver")),
        mac=data.get("mac", None),
        ap=ap,
        parent=parent,
        type=node_type,
        level=level,
        config=data.get("config"),
    )


def process_connection(data: str) -> dict[str, int]:
    """Process connection data."""

    # Check that the data is not empty
    if not isinstance(data, str) or data == "":
        return {}

    if data == "wired_mac":
        return {"connection_type": 0, "guest": 0}

    try:
        temp = data.split("_")
        return {
            "connection_type": CONNECTION_TYPE.get(temp[0]) or 0,
            "guest": int(temp[1]) if len(temp) > 1 else 0,
        }
    except Exception as ex:
        raise ex
