"""Convertors module for AsusRouter"""

from __future__ import annotations

from datetime import datetime, timedelta
import re

from asusrouter.error import AsusRouterValueError

BOOL_FALSE : tuple[str, ...] = ("false", "block", "0", )
BOOL_TRUE : tuple[str, ...] = ("true", "allow", "1", )
ERROR_VALUE = "Wrong value: {} with original exception: {}"
ERROR_VALUE_TYPE = "Wrong value {} of type {}"
REGEX_MAC = re.compile("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})")


def int_from_str(raw : str, base : int = 10) -> int:
    """Convert string to integer"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    raw = raw.strip()

    if raw == str():
        return int(0)

    return int(raw, base = base)


def float_from_str(raw : str) -> float:
    """Convert striing to float"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))
        
    raw = raw.strip()

    if raw == str():
        return float(0)

    return float(raw)


def bool_from_any(raw : str | int | float) -> bool:
    """Converts string or number to bool"""

    _type = type(raw)

    if (_type == int
        or _type == float
    ):
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
        raise ValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))


def none_or_str(raw : str) -> str | None:
    """Returns either string or None if string is empty"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    if raw.strip() == str():
        return None

    return raw.strip()


def timedelta_long(raw : str) -> timedelta:
    """Transform connection timedelta of the device to a proper datetime object when the device was connected"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))
        
    raw = raw.strip()

    if raw == str():
        return timedelta()

    part = raw.split(":")
    try:
        return timedelta(hours = int(part[-3]), minutes = int(part[-2]), seconds = int(part[-1]))
    except ValueError as ex:
        raise(AsusRouterValueError(ERROR_VALUE.format(raw, str(ex))))


def time_from_delta(raw : str) -> datetime:
    """Transform time delta to the date in the past"""

    return datetime.utcnow().replace(microsecond=0) - timedelta_long(raw)


def is_mac_address(raw : str) -> bool:
    """Checks if string is MAC address"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    raw = raw.strip()

    if raw == str():
        return False

    if re.search(REGEX_MAC, raw):
        return True

    return False


