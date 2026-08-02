"""Legacy login change for AsusRouter."""

from __future__ import annotations

from typing import Any

from asusrouter.const import RequestType
from asusrouter.modules.common.command import (
    ACTION_MODE_KEY,
    ARActionMode,
    ARService,
)
from asusrouter.modules.nvram import ARNvramType
from asusrouter.tools.writers import dict_to_request

# Services the WebUI runs on apply; the password persists from the nvram write
_LEGACY_SERVICES = (ARService.TIME_RESTART, ARService.UPNP_RESTART)
_LEGACY_ACTION_SCRIPT = "".join(f"{service};" for service in _LEGACY_SERVICES)


def build_legacy_request(username: str, password: str) -> str:
    """Build login credentials change body."""

    data: dict[str, Any] = {
        ACTION_MODE_KEY: str(ARActionMode.APPLY),
        "action_script": _LEGACY_ACTION_SCRIPT,
        ARNvramType.HTTP_USERNAME.value: username,
        ARNvramType.HTTP_PASSWORD.value: password,
        # Confirmation fields the WebUI form submits alongside the password
        "http_passwd2": password,
        "v_password2": password,
    }
    return dict_to_request(data, request_type=RequestType.GET)


__all__ = [
    "build_legacy_request",
]
