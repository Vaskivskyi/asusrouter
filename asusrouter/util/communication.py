"""Communication module for AsusRouter"""

import base64
import logging
from typing import Any, Tuple

import aiohttp

from asusrouter import (
    AsusRouterAuthorizationError,
    AsusRouterLoginBlockError,
    AsusRouterLoginError,
    AsusRouterResponseError,
    AsusRouterServerDisconnectedError,
    AsusRouterLoginAnotherError,
    AsusRouterLoginCaptchaError,
    AsusRouterResetRequiredError,
)
from asusrouter.const import (
    ANOTHER,
    AR_ERROR_CODE,
    AR_USER_AGENT,
    AUTHORIZATION,
    CAPTCHA,
    CREDENTIALS,
    ERROR_STATUS,
    LOGOUT,
    RESET_REQUIRED,
    SUCCESS,
    TRY_AGAIN,
)
from asusrouter.util import converters, parsers

_LOGGER = logging.getLogger(__name__)

def generate_credentials(username: str, password: str) -> Tuple[str, str]:
    """Generate credentials for connection"""

    auth = f"{username}:{password}".encode("ascii")
    logintoken = base64.b64encode(auth).decode("ascii")
    payload = f"login_authorization={logintoken}"
    headers = {"user-agent": AR_USER_AGENT}

    return payload, headers

def handle_error_codes(json_body: dict[str, Any]) -> None:
    """Handle reported error codes"""

    # ERROR CODES
    error_code = int(json_body[ERROR_STATUS])
    # Not authorized
    if error_code == AR_ERROR_CODE[AUTHORIZATION]:
        raise AsusRouterAuthorizationError("Session is not authorized")
    # Captcha required
    if error_code == AR_ERROR_CODE[CAPTCHA]:
        raise AsusRouterLoginCaptchaError("Device requires captcha")
    # Wrong crerdentials
    if error_code == AR_ERROR_CODE[CREDENTIALS]:
        raise AsusRouterLoginError("Wrong credentials")
    # Too many attempts
    if error_code == AR_ERROR_CODE[TRY_AGAIN]:
        raise AsusRouterLoginBlockError(
            "Too many attempts to login",
            timeout=converters.int_from_str(
                json_body["remaining_lock_time"]
            ),
        )
    # 10 wrong attempts - device blocked
    if error_code == AR_ERROR_CODE[RESET_REQUIRED]:
        raise AsusRouterResetRequiredError(
            "Device is blocked of the number of failed logins. Reset the device"
        )
    # Another user should log out
    if error_code == AR_ERROR_CODE[ANOTHER]:
        raise AsusRouterLoginAnotherError(
            "Another user should log out first"
        )
    # Loged out
    if error_code == AR_ERROR_CODE[LOGOUT]:
        return {SUCCESS: True}
    # Unknown error code
    raise AsusRouterResponseError(
        f"Unknown error code `{error_code}`, please report it"
    )

def handle_json_decode_error(string_body: str, endpoint: str) -> dict[str, Any]:
    """Handle a JSONDecodeError by attempting to parse the response as XML or pseudo-JSON"""

    if ".xml" in endpoint:
        json_body = parsers.xml(text=string_body)
    else:
        json_body = parsers.pseudo_json(text=string_body, page=endpoint)
    return json_body

def handle_server_disconnected_error(
    ex: aiohttp.ServerDisconnectedError,
    endpoint: str,
    payload: str,
    retry: bool,
) -> None:
    """Handle a ServerDisconnectedError"""

    if retry:
        raise AsusRouterServerDisconnectedError(ex) from ex
    _LOGGER.debug(
        "Disconnected by the device while quering '%s' with payload '%s'. "
        "Everything should recover by itself. If this warning appears regularly, "
        "you might need to decrease the number of simultaneous connections "
        "to your device",
        endpoint,
        payload,
    )
