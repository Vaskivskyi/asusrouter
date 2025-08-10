"""Result of processing firmware_001.content."""

from asusrouter import AsusData
from asusrouter.modules.firmware import (
    Firmware,
    WebsError,
    WebsFlag,
    WebsUpdate,
    WebsUpgrade,
)

_available: Firmware | None = Firmware(
    major="3.0.0.4", minor=388, build=4, revision=0
)
_available_beta: Firmware | None = None

expected_result = {
    AsusData.FIRMWARE: {
        "current": None,
        "state": True,
        "available": _available,
        "state_beta": False,
        "available_beta": _available_beta,
        "webs": {
            "update": WebsUpdate.INACTIVE,
            "upgrade": WebsUpgrade.INACTIVE,
            "available": _available,
            "available_beta": _available_beta,
            "required": None,
            "error": WebsError.NONE,
            "flag": WebsFlag.DONT,
            "level": 0,
        },
        "cfg": {
            "check": None,
            "upgrade": None,
        },
        "sig": {
            "update": 0,
            "upgrade": 1,
            "version": "2.380",
            "error": 0,
            "flag": 1,
        },
        "hndwr": {
            "status": 99,
        },
    },
}
