"""Service module."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Optional, Tuple

from asusrouter.error import AsusRouterServiceError
from asusrouter.tools.converters import safe_bool, safe_int

_LOGGER = logging.getLogger(__name__)


async def async_call_service(
    callback: Callable[..., Awaitable[dict[str, Any]]],
    service: Optional[str],
    arguments: Optional[dict[str, Any]] = None,
    apply: bool = False,
    expect_modify: bool = True,
) -> Tuple[bool, Optional[int], Optional[int]]:
    """Call a service."""

    # Generate commands
    commands = {}

    # Service call provided
    if service is not None:
        commands["rc_service"] = service

    # Check arguments
    if not arguments:
        arguments = {}

    # Add apply command if requested
    if apply:
        arguments["action_mode"] = "apply"

    # Add arguments to the commands
    commands.update(arguments)

    # Send the commands
    try:
        result = await callback(commands)
    except Exception as ex:  # pylint: disable=broad-except
        raise ex

    if service is not None:
        # Check if the service is run
        run_service = result.get("run_service", None)
        if run_service != service:
            raise AsusRouterServiceError(f"Service not run. Raw result: {result}")

    _LOGGER.debug(
        "Service `%s` run with arguments `%s`. Result: `%s`", service, arguments, result
    )

    last_id = result.get("id") or arguments.get("id")
    last_id = safe_int(last_id)

    needed_time = safe_int(result.get("restart_needed_time"))
    # For all the services with setting ID we better wait
    # before we will get actual state change
    if needed_time is None and last_id is not None:
        needed_time = 5

    # Special services that won't return any result
    if arguments.get("action_mode") == "update_client_list":
        return (True, needed_time, last_id)

    if expect_modify:
        return (safe_bool(result.get("modify")) or False, needed_time, last_id)

    return (True, needed_time, last_id)
