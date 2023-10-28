"""Service module."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Optional

from asusrouter.error import AsusRouterServiceError
from asusrouter.tools.converters import safe_bool

_LOGGER = logging.getLogger(__name__)


async def async_call_service(
    callback: Callable[..., Awaitable[dict[str, Any]]],
    service: str,
    arguments: Optional[dict[str, Any]] = None,
    apply: bool = False,
    expect_modify: bool = True,
) -> bool:
    """Call a service."""

    # Generate commands
    commands = {
        "rc_service": service,
    }

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

    run_service = result.get("run_service", None)
    if run_service != service:
        raise AsusRouterServiceError(f"Service not run. Raw result: {result}")

    _LOGGER.debug(
        "Service `%s` run with arguments `%s`. Result: `%s`", service, arguments, result
    )

    if expect_modify:
        return safe_bool(result.get("modify")) or False

    return True
