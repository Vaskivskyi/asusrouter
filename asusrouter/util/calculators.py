"""Calculators module for AsusRouter"""

from __future__ import annotations

from asusrouter.const import (
    CONST_ZERO,
    TOTAL,
    USED,
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
    previous_used: (int | float) = 0.0,
    previous_total: (int | float) = 0.0,
) -> float | None:
    """Calculate usage in percents"""

    # Handle zero usage
    if current_used == previous_used or current_total == previous_total:
        return 0.0

    # Calculate change
    used = current_used - previous_used
    total = current_total - previous_total

    # Handle any wrong input
    if used < 0 or total < 0 or used > total:
        return None

    # Handle zero total
    if total == 0:
        return 0.0

    return round(100 * used / total, 2)


def usage_in_dict(
    after: dict[str, (int | float)],
    before: dict[str, (int | float)] | None = None,
) -> dict[str, (int | float)]:
    """Calculate usage in percents in a dictionary"""

    if not before:
        before = {"used": 0.0, "total": 0.0}
    after["usage"] = usage(after["used"], after["total"], before["used"], before["total"])

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
