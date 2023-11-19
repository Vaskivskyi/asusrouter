"""Devicemap endpoint module."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Optional, Tuple

import xmltodict
from dateutil.parser import parse as dtparse

from asusrouter.modules.data import AsusData, AsusDataState
from asusrouter.modules.endpoint import data_get
from asusrouter.modules.openvpn import AsusOVPNClient, AsusOVPNServer
from asusrouter.tools.cleaners import clean_dict, clean_dict_key_prefix
from asusrouter.tools.converters import safe_int
from asusrouter.tools.readers import merge_dicts

from .devicemap_const import DEVICEMAP_BY_INDEX, DEVICEMAP_BY_KEY, DEVICEMAP_CLEAR

_LOGGER = logging.getLogger(__name__)

REQUIRE_HISTORY = True


def read(content: str) -> dict[str, Any]:
    """Read devicemap data."""

    # Create a dict to store the data
    devicemap: dict[str, Any] = {}

    # Parse the XML data
    try:
        xml_content: dict[str, Any] = xmltodict.parse(content).get("devicemap", {})
        if not xml_content:
            _LOGGER.debug("Received empty devicemap XML")
            return devicemap
    except xmltodict.expat.ExpatError as ex:  # type: ignore
        _LOGGER.debug("Received invalid devicemap XML: %s", ex)
        return devicemap

    # Go through the data and fill the dict

    # Get values by index using read_devicemap_index method
    devicemap = merge_dicts(devicemap, read_index(xml_content))

    # Get values by key using read_devicemap_key method
    devicemap = merge_dicts(devicemap, read_key(xml_content))

    # Clear values from useless symbols
    for output_group, clear_map in DEVICEMAP_CLEAR.items():
        if output_group not in devicemap:
            continue
        for key, clear_value in clear_map.items():
            # If the key is not in the devicemap, continue
            if key not in devicemap[output_group]:
                continue
            devicemap[output_group][key] = devicemap[output_group][key].replace(
                clear_value, ""
            )

    # Clean the devicemap values
    devicemap = clean_dict(devicemap)

    # Clean the devicemap values_dict from output_group prefix
    for output_group, values_dict in devicemap.items():
        devicemap[output_group] = clean_dict_key_prefix(values_dict, output_group)

    # Return the devicemap
    return devicemap


def read_index(xml_content: dict[str, Any]) -> dict[str, Any]:
    """Read devicemap by index.

    This method performs reading of the devicemap by index
    to simplify the original read_devicemap method."""

    # Create a dict to store the data
    devicemap: dict[str, Any] = {}

    # Get values for which we only know their order (index)
    for output_group, input_group, input_values in DEVICEMAP_BY_INDEX:
        # Create an empty dictionary for the output group
        devicemap[output_group] = {}

        # Check that the input group is in the xml content
        if input_group not in xml_content:
            continue

        # Use dict comprehension to build output_group_data
        output_group_data = {
            input_value: xml_content[input_group][index]
            for index, input_value in enumerate(input_values)
            if index < len(xml_content[input_group])
        }

        # Add the output group data to the devicemap
        devicemap[output_group] = output_group_data

    # Return the devicemap
    return devicemap


def read_key(xml_content: dict[str, Any]) -> dict[str, Any]:
    """Read devicemap by key.

    This method performs reading of the devicemap by key
    to simplify the original read_devicemap method."""

    # Create a dict to store the data
    devicemap: dict[str, Any] = {}

    # Get values for which we know their key
    for output_group, input_group, input_values in DEVICEMAP_BY_KEY:
        # Create a dict to store the data
        output_group_data: dict[str, Any] = {}

        # Go through the input values and fill the dict
        for input_value in input_values:
            # Get the input group data
            xml_input_group = xml_content.get(input_group)

            # If the input group data is None, skip this iteration
            if xml_input_group is None:
                continue

            # If the input group data is a string, convert it to a list
            if isinstance(xml_input_group, str):
                xml_input_group = [xml_input_group]

            # Go through the input group data and check if the input value is in it
            for value in xml_input_group:
                if input_value in value:
                    # Add the input value to the output group data
                    output_group_data[input_value] = value.replace(
                        f"{input_value}=", ""
                    )
                    break

        # Add the output group data to the devicemap
        devicemap[output_group] = output_group_data

    # Return the devicemap
    return devicemap


# This method performs reading of the devicemap special values
# pylint: disable-next=unused-argument
def read_special(xml_content: dict[str, Any]) -> dict[str, Any]:
    """Read devicemap special values."""

    # This method is not implemented yet

    return {}


def read_uptime_string(content: str) -> datetime | None:
    """Read uptime string and return proper datetime object."""

    # Split the content into the date/time part and the seconds part
    uptime_parts = content.split("(")
    if len(uptime_parts) < 2:
        return None

    # Extract the number of seconds from the seconds part
    seconds_match = re.search("([0-9]+)", uptime_parts[1])
    if not seconds_match:
        return None

    try:
        seconds = int(seconds_match.group())
        when = dtparse(uptime_parts[0])
    except ValueError:
        return None

    uptime = when - timedelta(seconds=seconds)

    return uptime


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process data from devicemap endpoint."""

    # Get the passed awrguments
    history: dict[AsusData, AsusDataState] = data_get(data, "history") or {}

    # Devicemap - just the data itself
    devicemap = data

    # Boot time
    prev_boottime_object: Optional[AsusDataState] = history.get(AsusData.BOOTTIME)
    prev_boottime = prev_boottime_object.data if prev_boottime_object else None
    boottime, reboot = process_boottime(devicemap, prev_boottime)

    # Mark reboot
    flags = {}
    if reboot:
        flags["reboot"] = True

    # OpenVPN
    openvpn = process_ovpn(devicemap)

    # Return the processed data
    return {
        AsusData.DEVICEMAP: devicemap,
        AsusData.BOOTTIME: boottime,
        AsusData.OPENVPN: openvpn,
        AsusData.FLAGS: flags,
    }


def process_boottime(
    devicemap: dict[str, Any], prev_boottime: Optional[dict[str, Any]]
) -> Tuple[dict[str, Any], bool]:
    """Process boottime data"""

    # Reboot flag
    reboot = False

    boottime = {}

    # Since precision is 1 second, could be that old and new are 1 sec different.
    # In this case, we should not change the boot time,
    # but keep the previous value to avoid regular changes
    sys = devicemap.get("sys")
    if sys:
        uptime_str = sys.get("uptimeStr")
        if uptime_str:
            time = read_uptime_string(uptime_str)
            if time:
                boottime["datetime"] = time

                if prev_boottime and "datetime" in prev_boottime:
                    delta = time - prev_boottime["datetime"]

                    # Check for reboot
                    if abs(delta.seconds) >= 2 and delta.seconds >= 0:
                        reboot = True
                    else:
                        boottime = prev_boottime

    return boottime, reboot


def process_ovpn(devicemap: dict[str, Any]) -> dict[str, Any]:
    """Process OpenVPN data"""

    vpn: dict[str, Any] = {
        "client": {},
        "server": {},
    }
    vpnmap = devicemap.get("vpn")

    if vpnmap:
        # There are only 5 clients actually in the current firmware
        # but we in case it will be ever changed in the future
        for num in range(1, 10):
            # Check if this client exists
            if f"client{num}_state" not in vpnmap:
                break

            # Get client data
            # We define default state as 0, since it's not always present
            client_state = AsusOVPNClient(
                safe_int(vpnmap.get(f"client{num}_state"), default=0)
            )
            client_errno = safe_int(vpnmap.get(f"client{num}_errno"))

            # Assign client data
            vpn["client"][num] = {
                "state": client_state,
                "errno": client_errno,
            }

        # Server data. Usually only 2 servers
        # but we in case it will be ever changed in the future
        for num in range(1, 5):
            # Check if this server exists
            if f"server{num}_state" not in vpnmap:
                break

            # Get server data
            # We define default state as 0, since it's not always present
            server_state = AsusOVPNServer(
                safe_int(vpnmap.get(f"server{num}_state"), default=0)
            )

            # Assign server data
            vpn["server"][num] = {
                "state": server_state,
            }

    return vpn
