"""Convertors module for AsusRouter"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse as dtparse
from typing import Any

from asusrouter.error import AsusRouterValueError

BOOL_FALSE: tuple[str, ...] = (
    "false",
    "block",
    "0",
    "off",
)
BOOL_TRUE: tuple[str, ...] = (
    "true",
    "allow",
    "1",
    "on",
)
ERROR_VALUE = "Wrong value: {} with original exception: {}"
ERROR_VALUE_TYPE = "Wrong value {} of type {}"
REGEX_MAC = re.compile("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})")


def int_from_str(raw: str, base: int = 10) -> int:
    """Convert string to integer"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    raw = raw.strip()

    if raw == str():
        return int(0)

    try:
        return int(raw, base=base)
    except ValueError as ex:
        raise AsusRouterValueError(ERROR_VALUE.format(raw, str(ex)))


def clean_html(raw: str) -> str:
    """Clean html tags"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    return re.sub("<([\/ibu]+)>", "", raw)


def bool_or_int(raw: str, base: int = 10) -> bool | int:
    """Convert to bool or to int"""

    if type(raw) != str:
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

    if type(raw) != str:
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
        raise AsusRouterValueError(ERROR_VALUE.format(raw, str(ex)))

    return value


def bool_from_any(raw: str | int | float) -> bool:
    """Converts string or number to bool"""

    _type = type(raw)

    if _type == int or _type == float:
        if raw == 0:
            return False
        else:
            return True

    elif _type == str:
        if raw.lower().strip() in BOOL_FALSE:
            return False
        elif raw.lower().strip() in BOOL_TRUE:
            return True
        else:
            raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    else:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))


def int_from_bool(raw: bool) -> int:
    """Convert boolean value to 0 or 1"""

    if type(raw) != bool:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    return 1 if raw else 0


def none_or_str(raw: str) -> str | None:
    """Returns either string or None if string is empty"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    if raw.strip() == str():
        return None

    return raw.strip()


def exists_or_not(raw: str) -> bool:
    """Returns whether value exists or is empty"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    if raw.strip() == str():
        return False

    return True


def timedelta_long(raw: str) -> timedelta:
    """Transform connection timedelta of the device to a proper datetime object when the device was connected"""

    if type(raw) != str:
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
        raise (AsusRouterValueError(ERROR_VALUE.format(raw, str(ex))))


def time_from_delta(raw: str) -> datetime:
    """Transform time delta to the date in the past"""

    return datetime.utcnow().replace(
        microsecond=0, tzinfo=timezone.utc
    ) - timedelta_long(raw)


def datetime_from_str(raw: str) -> datetime:
    """Transform string to datetime"""

    if type(raw) != str:
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

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    raw = raw.strip()

    if raw == str():
        return False

    if re.search(REGEX_MAC, raw):
        return True

    return False


def service_support(raw: str) -> list[str]:
    """Get the list of the supported services"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    services = list()

    if raw == str():
        return services

    services = raw.split(" ")
    services = [i for i in services if i]

    return services


def ovpn_remote_fom_str(raw: str) -> dict[str, Any]:
    """Get OpenVPN remote data"""

    if type(raw) != str:
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
