"""Home Assistant module for AsusRouter.

This module is used to convert some of the AsusRouter data
to a format easy to handle by Home Assistant integration.

Native AsusRouter integration: https://github.com/vaskivskyi/ha-asusrouter.
"""

from __future__ import annotations

from enum import Enum
import logging
from typing import Any

from asusrouter.modules.data import AsusData
from asusrouter.modules.state import AsusState
from asusrouter.tools.converters import flatten_dict, list_from_dict

_LOGGER = logging.getLogger(__name__)


def convert_to_ha_sensors(
    data: dict[str, Any], datatype: AsusData
) -> list[str]:
    """Convert available data.

    The result is a list of sensors compatible with Home Assistant.
    """

    return convert_to_ha_sensors_list(data)


def convert_to_ha_data(data: dict[str, Any]) -> dict[str, Any]:
    """Convert available data to the HA-compatible dictionary."""

    def convert_recursive(data: dict[str, Any]) -> dict[str, Any]:
        """Convert data to the HA-compatible dictionary recursively."""
        return {
            key: convert_recursive(value)
            if isinstance(value, dict)
            else convert_to_ha_state_bool(value)
            if key.endswith(("state", "link"))
            else value
            for key, value in data.items()
        }

    # Flatten the dictionary
    # Skip all the `list`, `clients` etc keys - this data should be preserved
    output = flatten_dict(data, exclude=["list", "clients", "rules"])

    # Convert values to HA-compatible format
    if output is not None:
        return convert_recursive(output)

    return {}


def convert_to_ha_sensors_group(data: dict[str, Any]) -> list[str]:
    """Convert the top level of data to the list of sensors."""

    return list_from_dict(data)


def convert_to_ha_sensors_list(data: dict[str, Any]) -> list[str]:
    """Convert all the available data to the list of sensors."""

    return list_from_dict(convert_to_ha_data(data))


def convert_to_ha_state_bool(
    data: AsusState | bool | None,
) -> bool | None:
    """Convers native state to a binary state."""

    # Check whether the state is None
    if data is None:
        return None

    # Check whether the state is already a bool
    if isinstance(data, bool):
        return data

    # Check whether the state is based on (int, Enum)
    if isinstance(data, int) and isinstance(data, Enum):
        return None if data.value < 0 else data.value > 0

    return None


def convert_to_ha_string(data: Any) -> str:
    """Convert data to a string."""

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
