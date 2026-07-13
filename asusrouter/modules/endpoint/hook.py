"""Hook endpoint module."""

from __future__ import annotations

import logging
from typing import Any

from asusrouter.modules.data import AsusData
from asusrouter.modules.led import AsusLED
from asusrouter.modules.parental_control import (
    KEY_PC_BLOCK_ALL,
    KEY_PC_STATE,
    AsusBlockAll,
    AsusParentalControl,
    read_pc_rules,
)
from asusrouter.tools.converters_v2.raw import raw_to_int

_LOGGER = logging.getLogger(__name__)

_VPNC_PART_MIN_FIELDS = 7


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process hook data."""

    # For this endpoint, the received data always depends on the sent request.
    # So, we need to check which data is available and process it accordingly.
    # Otherwise, we can accidentally overwrite the data with empty values.

    state: dict[AsusData, Any] = {}

    # LED
    if "led_val" in data:
        _led = raw_to_int(data.get("led_val"))
        state[AsusData.LED] = {
            "state": AsusLED(_led if _led is not None else -999)
        }

    # Parental control
    if KEY_PC_STATE in data:
        state[AsusData.PARENTAL_CONTROL] = process_parental_control(data)

    return state


def process_parental_control(data: dict[str, Any]) -> dict[str, Any]:
    """Process parental control data."""

    parental_control: dict[str, Any] = {}

    # State
    parental_control["state"] = AsusParentalControl(
        _v if (_v := raw_to_int(data.get(KEY_PC_STATE))) is not None else -999
    )

    # Block all
    _block_all = raw_to_int(data.get(KEY_PC_BLOCK_ALL))
    parental_control["block_all"] = AsusBlockAll(
        _block_all if _block_all is not None else -999
    )

    # Rules
    parental_control["rules"] = read_pc_rules(data)

    return parental_control
