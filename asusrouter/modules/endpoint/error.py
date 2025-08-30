"""Error endpoint module.

This is not an actual endpoint, but rather a module that is used
to handle errors from any endpoint.
"""

from __future__ import annotations

from enum import IntEnum
import logging
from typing import Any

from asusrouter.const import UNKNOWN_MEMBER, HTTPStatus
from asusrouter.error import (
    AsusRouterAccessError,
    AsusRouterLogoutError,
    AsusRouterRequestFormatError,
)
from asusrouter.modules.endpoint import EndpointType
from asusrouter.tools.readers import read_json_content

_LOGGER = logging.getLogger(__name__)


class AccessError(IntEnum):
    """Access error enum."""

    UNKNOWN = UNKNOWN_MEMBER

    SUCCESS = HTTPStatus.OK

    NO_ERROR = 0
    AUTHORIZATION = 2
    CREDENTIALS = 3
    TRY_AGAIN = 7
    LOGOUT = 8
    ANOTHER = 9
    CAPTCHA = 10
    RESET_REQUIRED = 11


def handle_access_error(
    endpoint: EndpointType, status: Any, headers: Any, content: Any
) -> None:
    """Handle access errors."""

    # Read the page as json
    message = read_json_content(content)

    # Get error code
    error_status = int(message.get("error_status") or UNKNOWN_MEMBER)
    # Formatting errors
    if error_status in (
        HTTPStatus.JSON_BAD_FORMAT,
        HTTPStatus.JSON_BAD_REQUEST,
    ):
        raise AsusRouterRequestFormatError("JSON format error")

    try:
        error = AccessError(error_status)
    except ValueError:
        error = AccessError.UNKNOWN

    # Success
    if error == AccessError.SUCCESS:
        return

    _LOGGER.debug("Access error message: %s", message)

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
