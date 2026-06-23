"""Temperature scaling for AsusRouter.

Helpers for rescaling temperature values that some routers report
orders of magnitude off, plus the one-time user notification.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, TypeVar

from asusrouter.config import ARConfigKey as ARConfKey
from asusrouter.tools.writers import ensure_notification_flag

_LOGGER = logging.getLogger(__name__)

EXPECTED_DECIMAL_PLACES = 2
EXPECTED_TEMPERATURE_MIN = 10.0
EXPECTED_TEMPERATURE_MAX = 150.0
MAX_SCALE_COUNT = 5

_temperature_warned_lock = threading.Lock()

# Scaling is agnostic to the key type used by the caller.
_K = TypeVar("_K")


def scale_temperature(
    temperature: dict[_K, float | None],
    range_min: float = EXPECTED_TEMPERATURE_MIN,
    range_max: float = EXPECTED_TEMPERATURE_MAX,
    max_scale_count: int = MAX_SCALE_COUNT,
) -> tuple[dict[_K, float], bool]:
    """Scale temperature values to a range.

    This is a temporary solution for those routers with orders of
    magnitude lower (or higher) temperature values.
    """

    scaled_temperature: dict[_K, float] = {}
    scaled = False

    for key, temp in temperature.items():
        if temp is None:
            continue

        scaled_temp = temp

        count = 0
        while scaled_temp < range_min and count < max_scale_count:
            scaled_temp *= 10
            count += 1

        while scaled_temp > range_max and count < max_scale_count:
            scaled_temp /= 10
            count += 1

        if scaled_temp != temp:
            scaled = True
        scaled_temperature[key] = round(scaled_temp, EXPECTED_DECIMAL_PLACES)

    return scaled_temperature, scaled


def warn_temperature_scaled(
    config: Any,
    variables: dict[str, Any],
) -> None:
    """Issue a one-time warning when temperature values are rescaled."""

    ensure_notification_flag(config, ARConfKey.NOTIFIED_OPTIMISTIC_TEMPERATURE)
    with _temperature_warned_lock:
        if config.get(ARConfKey.NOTIFIED_OPTIMISTIC_TEMPERATURE) is False:
            _LOGGER.warning(
                "Temperature values were rescaled due to the issue with "
                "the raw data. The original data is: "
                "`%s` and the expected range is between %s and %s.",
                variables,
                EXPECTED_TEMPERATURE_MIN,
                EXPECTED_TEMPERATURE_MAX,
            )
            config.set(ARConfKey.NOTIFIED_OPTIMISTIC_TEMPERATURE, True)
