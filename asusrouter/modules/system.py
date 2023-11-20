"""System module for AsusRouter."""

from __future__ import annotations

from enum import Enum
from typing import Any, Awaitable, Callable, Optional


class AsusSystem(str, Enum):
    """Asus system enum."""

    REBOOT = "reboot"
    RESTART_FIREWALL = "restart_firewall"
    RESTART_HTTPD = "restart_httpd"
    RESTART_WIRELESS = "restart_wireless"
    UPDATE_CLIENTS = "update_clients"


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusSystem,
    arguments: Optional[dict[str, Any]] = None,
    expect_modify: bool = False,
    extra_params: Optional[dict[Any, Any]] = None,
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
