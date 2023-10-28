"""Firmware endpoint module."""

from __future__ import annotations

import re
from typing import Any, Optional

from asusrouter.modules.data import AsusData
from asusrouter.modules.endpoint import data_get
from asusrouter.modules.firmware import Firmware, read_fw_string

REQUIRE_FIRMWARE = True


def read(content: str) -> dict[str, Any]:
    """Read firmware data"""

    firmware: dict[str, Any] = {}

    # Split the data into lines
    lines = content.splitlines()
    # Create a regex to match the data
    regex = re.compile(r"(\w+)\s*=\s*'(.*)';")
    # Go through the lines and fill the match data to the dict
    for line in lines:
        match = regex.match(line)
        if match:
            key, value = match.groups()
            firmware[key] = value

    return firmware


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process firmware data"""

    state: dict[AsusData, Any] = {}

    # Get the passed firmware
    firmware: Optional[Firmware] = data_get(data, "firmware") or None

    # Process firmware
    state[AsusData.FIRMWARE] = process_firmware(data, firmware) if data else {}

    return state


def process_firmware(raw_firmware, fw_current) -> dict[str, Any]:
    """Process firmware data"""

    # Firmware
    firmware = raw_firmware
    fw_new = read_fw_string(raw_firmware.get("webs_state_info", "")) or fw_current

    firmware["state"] = fw_current < fw_new
    firmware["current"] = str(fw_current)
    firmware["available"] = str(fw_new)

    return firmware
