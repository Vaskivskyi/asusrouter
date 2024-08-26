"""Firmware endpoint module."""

from __future__ import annotations

from typing import Any

from asusrouter.const import UNKNOWN_MEMBER
from asusrouter.modules.data import AsusData
from asusrouter.modules.firmware import (
    Firmware,
    WebsError,
    WebsFlag,
    WebsUpdate,
    WebsUpgrade,
)
from asusrouter.tools.converters import clean_string, safe_enum, safe_int
from asusrouter.tools.readers import read_js_variables as read  # noqa: F401

REQUIRE_FIRMWARE = True


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process firmware data."""

    # Stay on the safe side with Enums
    # since the endpoint can provide empty strings
    _available = Firmware(data.get("webs_state_info", "")).safe()
    _available_beta = Firmware(data.get("webs_state_info_beta", "")).safe()

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
                safe_int(data.get("webs_state_update")),
                default=WebsUpdate.UNKNOWN,
            ),
            "upgrade": safe_enum(
                WebsUpgrade,
                safe_int(data.get("webs_state_upgrade")),
                default=WebsUpgrade.INACTIVE,
            ),
            "available": _available,
            "available_beta": _available_beta,
            "required": Firmware(data.get("webs_state_REQinfo", "")).safe(),
            "error": safe_enum(
                WebsError,
                safe_int(data.get("webs_state_error")),
                default_value=UNKNOWN_MEMBER,
            ),
            "flag": safe_enum(
                WebsFlag,
                safe_int(data.get("webs_state_flag")),
                default_value=UNKNOWN_MEMBER,
            ),
            "level": safe_int(data.get("webs_state_level")),
        },
        "cfg": {
            "check": safe_int(data.get("cfg_check")),
            "upgrade": safe_int(data.get("cfg_upgrade")),
        },
        "sig": {
            "update": safe_int(data.get("sig_state_update")),
            "upgrade": safe_int(data.get("sig_state_upgrade")),
            "version": clean_string(data.get("sig_ver")),
            "error": safe_int(data.get("sig_state_error")),
            "flag": safe_int(data.get("sig_state_flag")),
        },
        "hndwr": {
            "status": safe_int(data.get("hndwr_status")),
        },
    }

    # Check the current firmware
    _current = data.get("firmware")
    firmware["current"] = _current

    # Check if the stable firmware is available
    firmware["state"] = (
        _current < _available if _current else _available is not None
    )
    if firmware["state"]:
        firmware["available"] = _available
    # Check if the beta firmware is available
    firmware["state_beta"] = (
        _current < _available_beta if _current else _available_beta is not None
    )
    if firmware["state_beta"]:
        firmware["available_beta"] = _available_beta

    return {AsusData.FIRMWARE: firmware}
