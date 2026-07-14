"""Endpoint error handling."""

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
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.tools.enum import FromIntMixin
from asusrouter.tools.readers import read_json_content

_LOGGER = logging.getLogger(__name__)


class ARAccessError(FromIntMixin, IntEnum):
    """Access error enum."""

    UNKNOWN = UNKNOWN_MEMBER

    SUCCESS = HTTPStatus.OK

    NO_ERROR = 0
    NO_TOKEN = 1
    AUTHORIZATION = 2
    CREDENTIALS = 3
    NO_REFERER = 4
    WEB_NO_REFERER = 5
    REFERER_FAILED = 6
    TRY_AGAIN = 7
    LOGOUT = 8
    ANOTHER = 9
    CAPTCHA = 10
    RESET_REQUIRED = 11


def handle_access_error(
    endpoint: AREndpoint, status: Any, headers: Any, content: Any
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
        error = ARAccessError(error_status)
    except ValueError:
        error = ARAccessError.UNKNOWN

    # Success
    if error == ARAccessError.SUCCESS:
        return

    _LOGGER.debug("Access error message: %s", message)

    # Additional values
    attributes: dict[str, Any] = {}

    # Handle logout code (even though it's not an error)
    if error == ARAccessError.LOGOUT:
        raise AsusRouterLogoutError("Session is logged out")

    # Try again later error
    if error == ARAccessError.TRY_AGAIN:
        timeout = message.get("remaining_lock_time")
        if timeout:
            attributes["timeout"] = int(timeout)

    # Return
    raise AsusRouterAccessError(
        "Access error",
        error,
        attributes,
    )
