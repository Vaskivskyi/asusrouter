"""Calculators module for AsusRouter"""

from __future__ import annotations

from asusrouter.const import (
    CONST_PERCENTS,
    CONST_ZERO,
    TOTAL,
    USAGE,
    USED,
    DEFAULT_USAGE_DIGITS,
    ERROR_ZERO_DIVISION,
)
from asusrouter.error import AsusRouterValueError

DEFAULT_USAGE_NONE = {
    TOTAL: 0,
    USED: 0,
}


def usage(
    current_used: (int | float),
    current_total: (int | float),
    previous_used: (int | float) = CONST_ZERO,
    previous_total: (int | float) = CONST_ZERO,
) -> float:
    """Calculate usage in percents"""

    if current_used == previous_used:
        return CONST_ZERO

    if current_total == previous_total:
        raise AsusRouterValueError(
            ERROR_ZERO_DIVISION.format("current_total == previous_total")
        )

    used = current_used - previous_used
    total = current_total - previous_total

    if used < 0:
        raise AsusRouterValueError(f"Usage cannot be negative, used = {used}")
    if total < 0:
        raise AsusRouterValueError(f"Usage cannot be negative, total = {total}")

    if used > total:
        raise AsusRouterValueError(
            "Usage cannot be above 100%, used = {used}, total = {total}"
        )

    return round(
        CONST_PERCENTS
        * (current_used - previous_used)
        / (current_total - previous_total),
        DEFAULT_USAGE_DIGITS,
    )


def usage_in_dict(
    after: dict[str, (int | float)],
    before: dict[str, (int | float)] | None = None,
) -> dict[str, (int | float)]:
    """Calculate usage in percents in a dictionary"""

    if not before:
        before = DEFAULT_USAGE_NONE
    after[USAGE] = usage(after[USED], after[TOTAL], before[USED], before[TOTAL])

    return after


def speed(
    after: (int | float),
    before: (int | float),
    time_delta: (int | float) | None = None,
) -> float:
    """Calculate speed"""

    if time_delta is None:
        return CONST_ZERO
    if time_delta == CONST_ZERO:
        raise AsusRouterValueError(ERROR_ZERO_DIVISION.format("time_delta"))

    diff = after - before if after > before else CONST_ZERO

    return diff / time_delta


def rgb(raw: dict[int, dict[str, int]]) -> dict[int, dict[str, int]]:
    """Calculate RGB values from input"""

    output = {}

    for led in raw:
        output[led] = {}
        for channel in raw[led]:
            value = raw[led][channel]
            if value < 0:
                output[led][channel] = 0
            elif value > 128:
                output[led][channel] = 128
            else:
                output[led][channel] = value

    return output
