"""Firmware endpoint module."""

from __future__ import annotations

from typing import Any

from asusrouter.const import UNKNOWN_MEMBER
from asusrouter.modules.data import AsusData
from asusrouter.modules.firmware import (
    ARFirmware,
    WebsError,
    WebsFlag,
    WebsUpdate,
    WebsUpgrade,
)
from asusrouter.tools.converters import clean_string, safe_enum
from asusrouter.tools.converters_v2.raw import raw_to_int
from asusrouter.tools.readers import read_js_variables

read = read_js_variables

REQUIRE_FIRMWARE = True


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process firmware data."""

    _fw = ARFirmware.from_string(data.get("webs_state_info"))
    _available = _fw if _fw.major is not None else None
    _fw = ARFirmware.from_string(data.get("webs_state_info_beta"))
    _available_beta = _fw if _fw.major is not None else None
    _fw = ARFirmware.from_string(data.get("webs_state_REQinfo"))
    _required = _fw if _fw.major is not None else None

    # Load all the static data
    firmware: dict[str, Any] = {
        "current": None,
        "state": False,
        "available": None,
        "state_beta": False,
        "available_beta": None,
        "webs": {
            "update": safe_enum(
                WebsUpdate,
                raw_to_int(data.get("webs_state_update")),
                default=WebsUpdate.UNKNOWN,
            ),
            "upgrade": safe_enum(
                WebsUpgrade,
                raw_to_int(data.get("webs_state_upgrade")),
                default=WebsUpgrade.INACTIVE,
            ),
            "available": _available,
            "available_beta": _available_beta,
            "required": _required,
            "error": safe_enum(
                WebsError,
                raw_to_int(data.get("webs_state_error")),
                default_value=UNKNOWN_MEMBER,
            ),
            "flag": safe_enum(
                WebsFlag,
                raw_to_int(data.get("webs_state_flag")),
                default_value=UNKNOWN_MEMBER,
            ),
            "level": raw_to_int(data.get("webs_state_level")),
        },
        "cfg": {
            "check": raw_to_int(data.get("cfg_check")),
            "upgrade": raw_to_int(data.get("cfg_upgrade")),
        },
        "sig": {
            "update": raw_to_int(data.get("sig_state_update")),
            "upgrade": raw_to_int(data.get("sig_state_upgrade")),
            "version": clean_string(data.get("sig_ver")),
            "error": raw_to_int(data.get("sig_state_error")),
            "flag": raw_to_int(data.get("sig_state_flag")),
        },
        "hndwr": {
            "status": raw_to_int(data.get("hndwr_status")),
        },
    }

    # Check the current firmware
    _current: ARFirmware | None = data.get("firmware")
    firmware["current"] = _current

    # Check if the stable firmware is available
    firmware["state"] = (
        _current < _available
        if _current is not None
        and _current.major is not None
        and _available is not None
        else _available is not None
    )
    if firmware["state"]:
        firmware["available"] = _available
    # Beta presence-only: beta revision strings ("2beta1" etc.) are typed
    # as MERLIN by translate_type, so cross-type __lt__ always returns False.
    firmware["state_beta"] = _available_beta is not None
    if firmware["state_beta"]:
        firmware["available_beta"] = _available_beta

    return {AsusData.FIRMWARE: firmware}
