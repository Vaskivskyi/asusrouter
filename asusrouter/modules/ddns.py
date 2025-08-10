"""DDNS module."""

from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Any

from asusrouter.tools.converters import clean_string, safe_bool


class AsusDDNS(IntEnum):
    """DDNS state values."""

    ACTIVE = 1
    INACTIVE = 0

    UNKNOWN = -999


class DDNSStatusCode(IntEnum):
    """DDNS status codes.

    Code comments show the original messages from the device code.
    """

    ERROR = -1
    NONE = 0
    SUCCESS = 200
    DOMAIN_TAKEN = 203
    REGISTERED_ORIGINAL = 220
    REGISTERED_NEW = 230
    NEW_DOMAIN_TAKEN = 233
    NOT_REGISTERED = 296
    CANNOT_START_WITH_NUMBER = 297
    INVALID_DOMAIN = 298
    INVALID_IP = 299
    SERVER_ERROR = 390
    UNAUTHORIZED = 401
    FIRMWARE_UPDATE_REQUIRED = 402
    PROXY_AUTH_REQUIRED = 407
    TIMEOUT = 1001  # For "Time-out"
    UNKNOWN_ERROR = 1002  # For "unknown_error"
    CONNECT_FAIL = 1003  # For "connect_fail"
    NO_CHANGE = 1004  # For "no_change"
    QUERY = 1005  # For "ddns_query"
    AUTH_FAIL = 1006  # For "auth_fail"
    OTHER = -999  # For any other non-empty code


class DDNSStatusHint(StrEnum):
    """DDNS status hints from the status code."""

    TIMEOUT = "Time-out"
    UNKNOWN_ERROR = "unknown_error"
    CONNECT_FAIL = "connect_fail"
    NO_CHANGE = "no_change"
    QUERY = "ddns_query"
    AUTH_FAIL = "auth_fail"
    OTHER = "other"


DDNS_HINT_MAP: dict[DDNSStatusHint, DDNSStatusCode] = {
    DDNSStatusHint.TIMEOUT: DDNSStatusCode.TIMEOUT,
    DDNSStatusHint.UNKNOWN_ERROR: DDNSStatusCode.UNKNOWN_ERROR,
    DDNSStatusHint.CONNECT_FAIL: DDNSStatusCode.CONNECT_FAIL,
    DDNSStatusHint.NO_CHANGE: DDNSStatusCode.NO_CHANGE,
    DDNSStatusHint.QUERY: DDNSStatusCode.QUERY,
    DDNSStatusHint.AUTH_FAIL: DDNSStatusCode.AUTH_FAIL,
    DDNSStatusHint.OTHER: DDNSStatusCode.OTHER,
}


DDNS_STATUS_HINT: dict[DDNSStatusCode, str] = {
    DDNSStatusCode.ERROR: "Request error! Please try again.",
    DDNSStatusCode.SUCCESS: "Registration is successful.",
    DDNSStatusCode.DOMAIN_TAKEN: (
        "This domain name '{hostname}' has been registered."
        " Please use a new domain name."
    ),
    DDNSStatusCode.REGISTERED_ORIGINAL: (
        "Registered the original hostname successfully."
    ),
    DDNSStatusCode.REGISTERED_NEW: "Registered the new hostname successfully.",
    DDNSStatusCode.NEW_DOMAIN_TAKEN: (
        "This domain name '{hostname}' has been registered."
        " The domain name you have registered is as followed: '{old_hostname}'"
    ),
    DDNSStatusCode.NOT_REGISTERED: (
        "The IP and hostname are not registered, please register first."
    ),
    DDNSStatusCode.CANNOT_START_WITH_NUMBER: (
        "The first character of the host name cannot be a number and the host"
        " name cannot include a period '.' (such as '123abc' or 'aaa.bbb')"
    ),
    DDNSStatusCode.INVALID_DOMAIN: (
        "Invalid Domain! The format should be 'xxx.asuscomm.com'."
    ),
    DDNSStatusCode.INVALID_IP: "Invalid IP Address!",
    DDNSStatusCode.SERVER_ERROR: "Server Error",
    DDNSStatusCode.UNAUTHORIZED: "Unauthorized registration request!",
    DDNSStatusCode.FIRMWARE_UPDATE_REQUIRED: (
        "Unable to register temporarily."
        " Please update your firmware to latest version and try later."
    ),
    DDNSStatusCode.PROXY_AUTH_REQUIRED: (
        "Client Error: Proxy Authentication Required!"
    ),
    DDNSStatusCode.TIMEOUT: (
        "No response from the DDNS server. Please try again."
    ),
    DDNSStatusCode.UNKNOWN_ERROR: "Request error! Please try again.",
    DDNSStatusCode.CONNECT_FAIL: "Unable to connect to the Internet",
    DDNSStatusCode.NO_CHANGE: (
        "Both hostname & IP address have not been changed"
        " since the last update."
    ),
    DDNSStatusCode.QUERY: "Processing",
    DDNSStatusCode.AUTH_FAIL: "Authentication failed.",
    DDNSStatusCode.OTHER: "Unknown status code",
}


DDNS_STATUS_ACTIVE: tuple[DDNSStatusCode, ...] = (
    DDNSStatusCode.SUCCESS,
    DDNSStatusCode.REGISTERED_ORIGINAL,
    DDNSStatusCode.REGISTERED_NEW,
)


# A helper to only consider status codes that are not hints
hint_codes = set(DDNS_HINT_MAP.values())


def read_ddns_status_code(raw: str | None) -> DDNSStatusCode:
    """Read DDNS status code."""

    raw = clean_string(raw)

    if not raw:
        return DDNSStatusCode.NONE

    # Check full-string match with hints
    for hint in DDNSStatusHint:
        if raw == hint.value:
            return DDNS_HINT_MAP.get(hint, DDNSStatusCode.OTHER)

    # Check code match in raw string, e.g. "200" which can be
    # a part of a longer string
    for code in DDNSStatusCode:
        if code in hint_codes or code == DDNSStatusCode.NONE:
            continue
        if str(code.value) in raw:
            return code

    # Unrecognized status
    return DDNSStatusCode.OTHER


def process_ddns(data: dict[str, str]) -> dict[str, Any]:
    """Process DDNS data."""

    ddns: dict[str, Any] = {
        "enabled": safe_bool(data.get("ddns_enable_x")),
        "hostname": clean_string(data.get("ddns_hostname_x")),
        "ip_address": clean_string(data.get("ddns_ipaddr")),
        "old_name": clean_string(data.get("ddns_old_name")),
        "replace_status": clean_string(data.get("ddns_replace_status")),
        "return_code": clean_string(data.get("ddns_return_code")),
        "server": clean_string(data.get("ddns_server_x")),
        "state": AsusDDNS.UNKNOWN,
        "status": DDNSStatusCode.NONE,
        "status_hint": "",
        "updated": safe_bool(data.get("ddns_updated")),
    }

    # Update the state based on the enabled status
    _status = read_ddns_status_code(data.get("ddns_return_code_chk"))
    ddns["status"] = _status
    ddns["status_hint"] = DDNS_STATUS_HINT.get(
        _status, DDNS_STATUS_HINT[DDNSStatusCode.OTHER]
    )

    if not ddns["enabled"]:
        ddns["state"] = AsusDDNS.INACTIVE
    else:
        ddns["state"] = (
            AsusDDNS.ACTIVE
            if _status in DDNS_STATUS_ACTIVE
            else AsusDDNS.INACTIVE
        )

    return ddns
