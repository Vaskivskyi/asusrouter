"""System module for AsusRouter."""

from __future__ import annotations

from enum import Enum
from typing import Any, Awaitable, Callable


class AsusSystem(str, Enum):
    """Asus system enum."""

    REBOOT = "reboot"
    REBUILD_AIMESH = "re_reconnect"
    RESTART_CHPASS = "restart_chpass"
    RESTART_DNSMASQ = "restart_dnsmasq"
    RESTART_FIREWALL = "restart_firewall"
    RESTART_HTTPD = "restart_httpd"
    RESTART_LEDS = "restart_leds"
    RESTART_OPENVPND = "restart_openvpnd"
    RESTART_SAMBA = "restart_samba"
    RESTART_TIME = "restart_time"
    RESTART_USB_IDLE = "restart_usb_idle"
    RESTART_VPNC = "restart_vpnc"
    RESTART_WIRELESS = "restart_wireless"
    RESTART_WGS = "restart_wgs"
    STOP_OPENVPND = "stop_openvpnd"
    STOP_VPNC = "stop_vpnc"
    UPDATE_CLIENTS = "update_clients"


# Map AsusSystem special cases to service calls
STATE_MAP: dict[AsusSystem, dict[str, Any]] = {
    AsusSystem.UPDATE_CLIENTS: {
        "service": None,
        "arguments": {"action_mode": "update_client_list"},
        "apply": False,
        "expect_modify": False,
    },
}


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusSystem,
    **kwargs: Any,
) -> bool:
    """Set the system state."""

    # Get the arguments for the callback function based on the state
    callback_args = STATE_MAP.get(
        state,
        {
            "service": state.value,
            "arguments": kwargs.get("arguments", {}),
            "apply": True,
            "expect_modify": kwargs.get("expect_modify", False),
        },
    )

    # Run the service
    return await callback(**callback_args)
