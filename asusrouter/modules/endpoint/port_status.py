"""Port Status endpoint module."""

from __future__ import annotations

import logging
from typing import Any

from asusrouter.modules.data import AsusData
from asusrouter.modules.ports import (
    PORT_CAP2TYPE,
    PORT_TYPE2LINK,
    PortCapability,
    PortSpeed,
    PortType,
)
from asusrouter.tools.converters import (
    get_enum_key_by_value,
    int_as_capabilities,
    safe_bool,
    safe_int,
)
from asusrouter.tools.readers import read_json_content as read  # noqa: F401

_LOGGER = logging.getLogger(__name__)


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process port status data"""

    ports: dict[PortType, Any] = {}

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

    nodes = {}

    for mac, info in node_info.items():
        # Save the node info
        nodes[mac] = info

    return nodes


def process_port_info(
    port: str, values: dict[str, Any]
) -> tuple[dict[str, Any], PortType, int]:
    """Process port info data."""

    # The port is a string with the format `port_label:port_id`
    # e.g. `L1` for LAN port 1 or `W0` for WAN port 0 (the main)
    # port_label = port[0]
    port_id = safe_int(port[1])

    # Get the capabilities of the port
    port_capabilities = int_as_capabilities(
        safe_int(values.get("cap")), PortCapability
    )

    # Get the port type
    port_type = PortType.UNKNOWN
    for pcap, ptype in PORT_CAP2TYPE.items():
        if port_capabilities.get(pcap) is True:
            port_type = ptype
            break

    # Get the correct link enum
    link_enum: Any = PORT_TYPE2LINK.get(port_type)

    # Get the rates. Set to 0 if not available
    link_rate = safe_int(values.get("link_rate"), default=0)
    max_rate = safe_int(values.get("max_rate"), default=0)

    if link_enum is not None:
        link_rate = get_enum_key_by_value(
            link_enum,
            link_rate,
            link_enum.UNKNOWN,
        )
        max_rate = get_enum_key_by_value(
            link_enum,
            max_rate,
            link_enum.UNKNOWN,
        )

    # Special ports
    if max_rate == PortSpeed.LINK_10000:
        if port_capabilities.get(PortCapability.SFPP) is True:
            port_type = PortType.SFPP

    # Port state
    port_state = safe_bool(values.get("is_on"))
    # For USB ports, the state is 1 only when a modem is connected
    modem = False
    port_devices = None
    if port_type == PortType.USB:
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
    if port_type == PortType.USB:
        port_description["modem"] = modem
        port_description["devices"] = port_devices

    return port_description, port_type, port_id
