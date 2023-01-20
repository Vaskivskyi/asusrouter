"""Convertors module for AsusRouter"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from dateutil.parser import parse as dtparse

from asusrouter.error import AsusRouterValueError

BOOL_FALSE: tuple[str, ...] = (
    "false",
    "block",
    "0",
    "off",
    "disabled",
)
BOOL_TRUE: tuple[str, ...] = (
    "true",
    "allow",
    "1",
    "on",
    "enabled",
)
ERROR_VALUE = "Wrong value: {} with original exception: {}"
ERROR_VALUE_TYPE = "Wrong value {} of type {}"
REGEX_MAC = re.compile("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})")

CONNECTION_TYPE = {
    "2G": 1,
    "5G": 2,
    "5G1": 3,
    "5G2": 3,
    "6G": 4,
}


def int_from_str(raw: str | int, base: int = 10) -> int:
    """Convert to integer"""

    if isinstance(raw, int):
        return raw

    if not isinstance(raw, str):
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    raw = raw.strip()

    if raw == str():
        return int(0)

    try:
        return int(raw, base=base)
    except ValueError as ex:
        raise AsusRouterValueError(ERROR_VALUE.format(raw, str(ex))) from ex


def clean_html(raw: str) -> str:
    """Clean html tags"""

    if not isinstance(raw, str):
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    return re.sub(r"<([\/ibu]+)>", "", raw)


def bool_or_int(raw: str | bool, base: int = 10) -> bool | int:
    """Convert to bool or to int"""

    if isinstance(raw, bool):
        return raw

    if not isinstance(raw, str):
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    raw = clean_html(raw)

    try:
        return int_from_str(raw, base)
    except AsusRouterValueError:
        """Do nothing"""
    try:
        return bool_from_any(raw)
    except AsusRouterValueError:
        """Do nothing"""

    raise AsusRouterValueError(ERROR_VALUE.format(raw))


def float_from_str(raw: str) -> float:
    """Convert striing to float"""

    if not isinstance(raw, str):
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    raw = raw.strip()

    if raw == str():
        return float(0)
    # For devices reporrting speeds with M at the end for mega
    if raw[-1] == "M":
        raw = raw[:-1]

    try:
        value = float(raw)
    except ValueError as ex:
        raise AsusRouterValueError(ERROR_VALUE.format(raw, str(ex))) from ex

    return value


def bool_from_any(raw: str | int | float | bool) -> bool | None:
    """Converts string or number to bool"""

    _type = type(raw)

    if _type == bool:
        return raw

    if _type in (int, float):
        if raw == 0:
            return False
        return True

    if _type == str:
        if raw.lower().strip() in BOOL_FALSE:
            return False
        if raw.lower().strip() in BOOL_TRUE:
            return True
        if raw == str():
            return None
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))


def int_from_bool(raw: bool) -> int:
    """Convert boolean value to 0 or 1"""

    if not isinstance(raw, bool):
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    return 1 if raw else 0


def none_or_any(raw: Any) -> None | Any:
    """Return value or process it with none_or_str"""

    if isinstance(raw, str):
        return none_or_str(raw)

    return raw


def none_or_str(raw: str) -> str | None:
    """Returns either string or None if string is empty"""

    if raw is None:
        return None

    if not isinstance(raw, str):
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    if raw.strip() == str():
        return None

    return raw.strip()


def exists_or_not(raw: str) -> bool:
    """Returns whether value exists or is empty"""

    if not isinstance(raw, str):
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    if raw.strip() == str():
        return False

    return True


def timedelta_long(raw: str) -> timedelta:
    """Transform connection timedelta of the device to a proper
    datetime object when the device was connected"""

    if not isinstance(raw, str):
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    raw = raw.strip()

    if raw == str():
        return timedelta()

    part = raw.split(":")
    try:
        return timedelta(
            hours=int(part[-3]), minutes=int(part[-2]), seconds=int(part[-1])
        )
    except ValueError as ex:
        raise (AsusRouterValueError(ERROR_VALUE.format(raw, str(ex)))) from ex


def time_from_delta(raw: str) -> datetime:
    """Transform time delta to the date in the past"""

    return datetime.utcnow().replace(
        microsecond=0, tzinfo=timezone.utc
    ) - timedelta_long(raw)


def datetime_from_str(raw: str) -> datetime:
    """Transform string to datetime"""

    if not isinstance(raw, str):
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))
    raw = raw.strip()
    if raw == str():
        return {}

    try:
        return dtparse(raw)
    except Exception as ex:
        raise ex


def is_mac_address(raw: str) -> bool:
    """Checks if string is MAC address"""

    if not isinstance(raw, str):
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    raw = raw.strip()

    if raw == str():
        return False

    if re.search(REGEX_MAC, raw):
        return True

    return False


def service_support(raw: str) -> list[str]:
    """Get the list of the supported services"""

    if not isinstance(raw, str):
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    services = []

    if raw == str():
        return services

    services = raw.split(" ")
    services = [i for i in services if i]

    return services


def ovpn_remote_fom_str(raw: str) -> dict[str, Any]:
    """Get OpenVPN remote data"""

    if not isinstance(raw, str):
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    try:
        temp = raw.split(",")
        auth = temp[1]
        temp = temp[0].split(":")
        ip = temp[0]
        port = int_from_str(temp[1])

        return {
            "ip": ip,
            "port": port,
            "auth": auth,
        }
    except Exception as ex:
        raise ex


def to_snake_case(raw: str):
    """Convert string to snake_case"""

    if not isinstance(raw, str):
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    string = (
        re.sub(r"(?<=[a-z])(?=[A-Z])|[^a-zA-Z]", " ", raw).strip().replace(" ", "_")
    )
    result = "".join(string.lower())
    while "__" in result:
        result = result.replace("__", "_")

    return result


def as_list(raw: Any):
    """Convert object into list of objects"""

    if not isinstance(raw, list):
        return [raw]

    return raw


def onboarding_connection(raw: str) -> dict[str, int]:
    """Convert connection type from onboarding type to native type"""

    if not isinstance(raw, str):
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    if raw == "wired_mac":
        return {
            "connection_type": 0,
            "guest": 0,
        }

    try:
        temp = raw.split("_")
        return {
            "connection_type": CONNECTION_TYPE.get(temp[0]),
            "guest": temp[1] if len(temp) > 1 else 0,
        }
    except Exception as ex:
        raise ex
