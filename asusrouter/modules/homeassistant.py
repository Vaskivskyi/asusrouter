"""Home Assistant module for AsusRouter.

This module is used to convert some of the AsusRouter data
to a format easy to handle by Home Assistant integration.

Native AsusRouter integration: https://github.com/vaskivskyi/ha-asusrouter."""


from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Optional

from asusrouter.modules.data import AsusData
from asusrouter.modules.state import AsusState
from asusrouter.modules.vpnc import AsusVPNC
from asusrouter.tools.converters import flatten_dict, list_from_dict

_LOGGER = logging.getLogger(__name__)

SENSORS_CPU = ["total", "usage", "used"]
SENSORS_NETWORK = ["rx", "rx_speed", "tx", "tx_speed"]
SENSORS_VPN = {
    "client": [
        "state",
        "remote",
        "datetime",
        "tun_tap_read",
        "tun_tap_write",
        "tcp_udp_read",
        "tcp_udp_write",
        "auth_read",
        "pre_compress",
        "post_compress",
        "pre_decompress",
        "post_decompress",
    ],
    "server": ["state", "client_list", "routing_table"],
}


def convert_to_ha_sensors(data: dict[str, Any], datatype: AsusData) -> list[str]:
    """Convert available data to the list of sensors
    compatible with Home Assistant."""

    sensors = []

    match datatype:
        case AsusData.CPU:
            sensors = convert_to_ha_sensors_by_map(data, SENSORS_CPU)
        case AsusData.NETWORK:
            sensors = convert_to_ha_sensors_by_map(data, SENSORS_NETWORK)
        case AsusData.OPENVPN:
            sensors = convert_to_ha_sensors_by_map_2(data, SENSORS_VPN)
        # case AsusData.PORTS:
        case _:
            sensors = convert_to_ha_sensors_list(data)

    return sensors


def convert_to_ha_data(data: dict[str, Any]) -> dict[str, Any]:
    """Convert available data to the HA-compatible dictionary."""

    def convert_recursive(data: dict[str, Any]) -> dict[str, Any]:
        """Convert data to the HA-compatible dictionary recursively."""
        return {
            key: convert_recursive(value)
            if isinstance(value, dict)
            else convert_to_ha_state_bool(value)
            if key.endswith("state") or key.endswith("link")
            else value
            for key, value in data.items()
        }

    # Flatten the dictionary
    # Skip all the `list`, `clients` etc keys - this data should be preserved
    output = flatten_dict(data, exclude=["list", "clients", "rules"])

    # Convert values to HA-compatible format
    if output is not None:
        output = convert_recursive(output)
        return output

    return {}


def convert_to_ha_sensors_by_map(
    data: dict[str, Any], sensor_map: list[str]
) -> list[str]:
    """Convert available data to the list of sensors
    using static map."""

    _LOGGER.debug("Converting data to the list of sensors by map: %s", data)

    sensors = []

    for sensor in data:
        for sensor_type in sensor_map:
            sensors.append(f"{sensor}_{sensor_type}")

    return sensors


def convert_to_ha_sensors_by_map_2(
    data: dict[str, Any], sensor_map: dict[str, list[str]]
) -> list[str]:
    """Convert available data to the list of sensors
    using first two levels of the data and static map."""

    _LOGGER.debug("Converting data to the list of sensors by 2 levels: %s", data)

    sensors = []

    for sensor in data:
        for sensor_id in data[sensor]:
            for sensor_type in sensor_map.get(sensor, []):
                sensors.append(f"{sensor}_{sensor_id}_{sensor_type}")

    return sensors


def convert_to_ha_sensors_group(data: dict[str, Any]) -> list[str]:
    """Convert the top level of data to the list of sensors."""

    return list_from_dict(data)


def convert_to_ha_sensors_list(data: dict[str, Any]) -> list[str]:
    """Convert all the available data to the list of sensors."""

    return list_from_dict(convert_to_ha_data(data))


def convert_to_ha_state_bool(data: AsusState | Optional[bool]) -> Optional[bool]:
    """Convers native state to a binary state."""

    # Check whether the state is None
    if data is None:
        return None

    # Check whether the state is already a bool
    if isinstance(data, bool):
        return data

    # Special cases
    if isinstance(data, AsusVPNC):
        match data:
            case a if a in (AsusVPNC.CONNECTED, AsusVPNC.CONNECTING, AsusVPNC.ON):
                return True
            case a if a in (AsusVPNC.OFF, AsusVPNC.DISCONNECTED, AsusVPNC.ERROR):
                return False
            case _:
                return None

    # Check whether the state is based on (int, Enum)
    if isinstance(data, int) and isinstance(data, Enum):
        if data.value == 0:
            return False
        if data.value > 0:
            return True
        if data.value < 0:
            return None

    return None


def convert_to_ha_string(data: Any) -> str:
    """Converts data to a string."""

    # Check if we have None
    if data is None:
        return ""

    # If we have an enum
    # Check whether value is an enum or a string
    # If string, return it, if enum, go recursive
    if isinstance(data, Enum):
        return convert_to_ha_string(data.value)

    # Check if we have string
    if isinstance(data, str):
        return data

    # For any other type, return string representation
    return str(data)
