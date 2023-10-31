"""Data transform module."""

from __future__ import annotations

from typing import Any, Optional

from asusrouter.modules.client import process_client
from asusrouter.modules.data import AsusDataState
from asusrouter.tools.readers import readable_mac


def transform_network(
    data: dict[str, Any],
    services: Optional[list[str]],
    history: Optional[AsusDataState],
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
    return network


def transform_clients(
    data: dict[str, Any],
    history: Optional[AsusDataState],
) -> dict[str, Any]:
    """Transform clients data."""

    clients = {}
    for mac, client in data.items():
        if readable_mac(mac):
            # Check client history
            client_history = history.data.get(mac) if history and history.data else None
            # Process the client
            clients[mac] = process_client(client, client_history)

    return clients
