"""Data transform module."""

from __future__ import annotations

from typing import Any, Optional

from asusrouter.modules.client import process_client
from asusrouter.modules.data import AsusDataState
from asusrouter.modules.ports import PortType
from asusrouter.tools.readers import readable_mac

# List of models with 6Ghz support
# and no 5Ghz2 support
MODEL_WITH_6GHZ = [
    "RT-AXE95Q",
]


def transform_network(
    data: dict[str, Any],
    services: Optional[list[str]],
    history: Optional[AsusDataState],
    **kwargs: Any,
) -> dict[str, Any]:
    """Transform network data."""

    # Check if the device has dualwan support
    if not services:
        return data
    if not "dualwan" in services:
        return data

    network = data.copy()
    # Add speed if not available - fix first empty value round
    for interface in network:
        for speed in ("rx_speed", "tx_speed"):
            if not speed in network[interface]:
                network[interface][speed] = 0.0

    # Add usb network if not available
    if not "usb" in network:
        # Check history
        usb_history = history.data.get("usb") if history and history.data else None
        # Revert to history if available
        if usb_history:
            network["usb"] = usb_history
            network["usb"]["rx_speed"] = 0.0
            network["usb"]["tx_speed"] = 0.0
        else:
            network["usb"] = {
                "rx": 0,
                "tx": 0,
                "rx_speed": 0.0,
                "tx_speed": 0.0,
            }

    # Get the model if available
    model = kwargs.get("model", None)

    # Check if we have 5GHz2 available in the network data
    if "5ghz2" in network:
        # Check interfaces for 5Ghz2/6Ghz
        support_5ghz2 = "5G-2" in services
        support_6ghz = "wifi6e" in services

        if (
            support_5ghz2 is False and support_6ghz is True
        ) or model in MODEL_WITH_6GHZ:
            # Rename 5Ghz2 to 6Ghz
            network["6ghz"] = network.pop("5ghz2")

    return network


def transform_clients(
    data: dict[str, Any], history: Optional[AsusDataState], **kwargs: Any
) -> dict[str, Any]:
    """Transform clients data."""

    clients = {}
    for mac, client in data.items():
        if readable_mac(mac):
            # Check client history
            client_history = history.data.get(mac) if history and history.data else None
            # Process the client
            clients[mac] = process_client(client, client_history, **kwargs)

    return clients


def transform_cpu(
    data: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Transform cpu data."""

    for info in data.values():
        info.setdefault("usage", None)

    return data


def transform_ethernet_ports(
    data: dict[str, Any],
    mac: Optional[str],
) -> dict[str, dict[str, Any]]:
    """Transform the legacy ethernet ports data to the new format."""

    # Check if the first level of the dict is PortType enum
    # If any other key is found, return the data as is
    for data_key in data:
        if not isinstance(data_key, PortType):
            return data

    # If mac is not available, return the data as is
    if not mac:
        return data

    # Transform the data
    return {mac: data}


def transform_wan(
    data: dict[str, Any],
    services: Optional[list[str]],
) -> dict[str, Any]:
    """Transform WAN data."""

    wan = data.copy()

    if not services:
        return wan

    service_keys = {"dualwan": "dualwan", "wanbonding": "aggregation"}

    for service, key in service_keys.items():
        if service not in services:
            wan.pop(key, None)

    return wan
