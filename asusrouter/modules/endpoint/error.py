"""Error endpoint module.

This is not an actual endpoint, but rather a module that is used to handle errors
from any endpoint."""

from __future__ import annotations

import logging
from enum import IntEnum
from typing import Any

from asusrouter.error import AsusRouterAccessError, AsusRouterLogoutError
from asusrouter.tools.readers import read_json_content

_LOGGER = logging.getLogger(__name__)


class AccessError(IntEnum):
    """Access error enum."""

    UNKNOWN = -999

    NO_ERROR = 0
    AUTHORIZATION = 2
    CREDENTIALS = 3
    TRY_AGAIN = 7
    LOGOUT = 8
    ANOTHER = 9
    CAPTCHA = 10
    RESET_REQUIRED = 11


def handle_access_error(endpoint, status, headers, content):
    """Handle access errors."""

    # Read the page as json
    message = read_json_content(content)
    _LOGGER.debug("Access error message: %s", message)

    # Get error code
    error_status = int(message.get("error_status") or -999)
    try:
        error = AccessError(error_status)
    except ValueError:
        error = AccessError.UNKNOWN

    # Additional values
    attributes: dict[str, Any] = {}

    # Handle logout code (even though it's not an error)
    if error == AccessError.LOGOUT:
        raise AsusRouterLogoutError("Session is logged out")

    # Try again later error
    if error == AccessError.TRY_AGAIN:
        timeout = message.get("remaining_lock_time")
        if timeout:
            attributes["timeout"] = int(timeout)

    # Return
    raise AsusRouterAccessError(
        "Access error",
        error,
        attributes,
    )
