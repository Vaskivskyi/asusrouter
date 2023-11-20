"""System module for AsusRouter."""

from __future__ import annotations

from enum import Enum
from typing import Any, Awaitable, Callable, Optional


class AsusSystem(str, Enum):
    """Asus system enum."""

    REBOOT = "reboot"
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


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusSystem,
    arguments: Optional[dict[str, Any]] = None,
    expect_modify: bool = False,
    _: Optional[dict[Any, Any]] = None,
) -> bool:
    """Set the LED state."""

    # Check if arguments are available
    if not arguments:
        arguments = {}

    # Special cases
    if state == AsusSystem.UPDATE_CLIENTS:
        return await callback(
            service=None,
            arguments={"action_mode": "update_client_list"},
            apply=False,
            expect_modify=False,
        )

    # Run the service
    return await callback(
        service=state.value,
        arguments={},
        apply=True,
        expect_modify=expect_modify,
    )
