"""Port Status endpoint module."""

from __future__ import annotations

import logging
from typing import Any

from asusrouter.modules.data import AsusData
from asusrouter.modules.ports import (
    ARPortCapability,
    ARPortEthernetSpeed,
    ARPortType,
    read_port_capabilities,
    read_port_speed,
    read_port_type,
)
from asusrouter.tools.converters import safe_bool, safe_int

_LOGGER = logging.getLogger(__name__)


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process port status data."""

    ports: dict[ARPortType, Any] = {}

    if not data:
        return {
            AsusData.PORTS: ports,
            AsusData.NODE_INFO: {},
        }

    state: dict[AsusData, Any] = {}

    # Node info
    state[AsusData.NODE_INFO] = process_node_info(data)

    # Port info
    port_info = data.get("port_info", {})
    if port_info:
        for mac, info in port_info.items():
            ports[mac] = {}

            for port, values in info.items():
                # Process the port info
                port_description, port_type, port_id = process_port_info(
                    port, values
                )

                # Create a port type group if it doesn't exist yet
                if port_type not in ports[mac]:
                    ports[mac][port_type] = {}

                # Save the port info
                ports[mac][port_type][port_id] = port_description

    state[AsusData.PORTS] = ports

    return state


def process_node_info(data: dict[str, Any]) -> dict[str, Any]:
    """Process node info data."""

    node_info = data.get("node_info", {})

    if not node_info:
        return {}

    return dict(node_info.items())


def process_port_info(
    port: str, values: dict[str, Any]
) -> tuple[dict[str, Any], ARPortType, int]:
    """Process port info data."""

    # The port is a string with the format `port_label:port_id`
    # e.g. `L1` for LAN port 1 or `W0` for WAN port 0 (the main)
    # port_label = port[0]
    port_id = safe_int(port[1])

    # Get the capabilities of the port
    port_capabilities = read_port_capabilities(values.get("cap"))

    # Get the port type
    port_type = read_port_type(port_capabilities)

    # Get the rates
    link_rate = read_port_speed(
        port_type, safe_int(values.get("link_rate"), default=0)
    )
    max_rate = read_port_speed(
        port_type, safe_int(values.get("max_rate"), default=0)
    )

    # Special ports
    if (
        max_rate == ARPortEthernetSpeed.MBPS_10000
        and port_capabilities.get(ARPortCapability.SFPP) is True
    ):
        port_type = ARPortType.SFPP

    # Port state
    port_state = safe_bool(values.get("is_on"))
    # For USB ports, the state is 1 only when a modem is connected
    modem = False
    port_devices = None
    if port_type == ARPortType.USB:
        # Mark a modem as connected
        if port_state is True:
            modem = True
        # If any other device is connected, mark as connected
        port_devices = values.get("devices")
        if port_devices is not None:
            port_state = True

    # Leave only the capabilities that are available
    capabilities = [
        capability
        for capability, value in port_capabilities.items()
        if value is True
    ]

    # Combine the port description
    port_description = {
        "state": port_state,
        "id": port_id,
        "capabilities": capabilities,
        "link_rate": link_rate,
        "max_rate": max_rate,
    }

    # Add the modem flag if needed and the connected devices
    if port_type == ARPortType.USB:
        port_description["modem"] = modem
        port_description["devices"] = port_devices

    return port_description, port_type, port_id
