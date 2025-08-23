"""Temperature endpoint module."""

from __future__ import annotations

import logging
import threading
from typing import Any

from asusrouter.config import ARConfig, ARConfigKey as ARConfKey
from asusrouter.modules.data import AsusData
from asusrouter.modules.wlan import Wlan
from asusrouter.tools.cleaners import clean_content
from asusrouter.tools.converters import safe_float
from asusrouter.tools.readers import read_js_variables
from asusrouter.tools.writers import ensure_notification_flag

_LOGGER = logging.getLogger(__name__)

EXPECTED_DECIMAL_PLACES = 2
EXPECTED_TEMPERATURE_MIN = 10.0
EXPECTED_TEMPERATURE_MAX = 150.0
MAX_SCALE_COUNT = 5

_temperature_warned_lock = threading.Lock()


# The temperature data can be presented it the following JS variables:
# 1) curr_coreTmp_2_raw, curr_coreTmp_5_raw, curr_coreTmp_52_raw
# 2) curr_coreTmp_0_raw, curr_coreTmp_1_raw, curr_coreTmp_2_raw,
# curr_coreTmp_3_raw
# 3) curr_coreTmp_wl0_raw, curr_coreTmp_wl1_raw, curr_coreTmp_wl2_raw,
# curr_coreTmp_wl3_raw
# for 2ghz, 5ghz, 5ghz2, 6ghz respectively
# CPU temperature is set either in curr_cpuTemp or curr_coreTmp_cpu
def read(content: str, **kwargs: Any) -> dict[str, Any]:
    """Read temperature data."""

    temperature: dict[str, Any] = {}

    # Get the correct configuration to proceed
    config = kwargs.get("config", ARConfig)

    # Prepare the content. This page is a set of JS variables
    variables = read_js_variables(clean_content(content))

    # Read WLAN temperatures
    # If there is curr_coreTmp_5_raw, we have type 1
    if "curr_coreTmp_5_raw" in variables:
        temperature[Wlan.FREQ_2G] = variables.get("curr_coreTmp_2_raw")
        temperature[Wlan.FREQ_5G] = variables.get("curr_coreTmp_5_raw")
        temperature[Wlan.FREQ_5G2] = variables.get("curr_coreTmp_52_raw")
    # If there is curr_coreTmp_0_raw, we have type 2
    elif "curr_coreTmp_0_raw" in variables:
        temperature[Wlan.FREQ_2G] = variables.get("curr_coreTmp_0_raw")
        temperature[Wlan.FREQ_5G] = variables.get("curr_coreTmp_1_raw")
        temperature[Wlan.FREQ_5G2] = variables.get("curr_coreTmp_2_raw")
        temperature[Wlan.FREQ_6G] = variables.get("curr_coreTmp_3_raw")
    # If there is curr_coreTmp_wl0_raw, we have type 3
    elif "curr_coreTmp_wl0_raw" in variables:
        temperature[Wlan.FREQ_2G] = variables.get("curr_coreTmp_wl0_raw")
        temperature[Wlan.FREQ_5G] = variables.get("curr_coreTmp_wl1_raw")
        temperature[Wlan.FREQ_5G2] = variables.get("curr_coreTmp_wl2_raw")
        temperature[Wlan.FREQ_6G] = variables.get("curr_coreTmp_wl3_raw")

    # Clean the temperature values from `&deg;C`
    for key, value in temperature.items():
        if value:
            temperature[key] = value.replace("&deg;C", "")

    # Read CPU temperature
    # If there is curr_coreTmp_cpu
    if "curr_coreTmp_cpu" in variables:
        temperature["cpu"] = variables.get("curr_coreTmp_cpu")
    # If there is curr_cpuTemp
    elif "curr_cpuTemp" in variables:
        temperature["cpu"] = variables.get("curr_cpuTemp")

    # Convert the temperature values to float or remove them
    # if they have "disabled"
    temperature = {
        key: safe_float(value)
        for key, value in temperature.items()
        if value and "disabled" not in value
    }

    # While this functional is performing a kind of post-processing,
    # it should stay a part of the read method to have access to the raw data
    if config.get(ARConfKey.OPTIMISTIC_TEMPERATURE):
        temperature, scaled = _scale_temperature(temperature)
        # Check if notification flag is registered
        ensure_notification_flag(
            config, ARConfKey.NOTIFIED_OPTIMISTIC_TEMPERATURE
        )
        with _temperature_warned_lock:
            if (
                scaled
                and config.get(ARConfKey.NOTIFIED_OPTIMISTIC_TEMPERATURE)
                is False
            ):
                _LOGGER.warning(
                    "Temperature values were rescaled due to the issue with "
                    "the raw data. The original data is: "
                    "`%s` and the expected range is between %s and %s.",
                    variables,
                    EXPECTED_TEMPERATURE_MIN,
                    EXPECTED_TEMPERATURE_MAX,
                )
                config.set(ARConfKey.NOTIFIED_OPTIMISTIC_TEMPERATURE, True)

    return temperature


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process temperature data."""

    temperature: dict[AsusData, Any] = {
        AsusData.TEMPERATURE: data,
    }

    return temperature


def _scale_temperature(
    temperature: dict[str, float | None],
    range_min: float = EXPECTED_TEMPERATURE_MIN,
    range_max: float = EXPECTED_TEMPERATURE_MAX,
    max_scale_count: int = MAX_SCALE_COUNT,
) -> tuple[dict[str, float], bool]:
    """Scale temperature values to a range.

    This method is a temporary solution for those routers
    with orders of magnitude lower temperature values.
    """

    scaled_temperature = {}
    scaled = False

    for key, temp in temperature.items():
        if temp is None:
            continue

        scaled_temp = temp

        count = 0
        # Scale up if too small
        while scaled_temp < range_min and count < max_scale_count:
            scaled_temp *= 10
            count += 1

        # Scale down if too large
        while scaled_temp > range_max and count < max_scale_count:
            scaled_temp /= 10
            count += 1

        if scaled_temp != temp:
            scaled = True
        scaled_temperature[key] = round(scaled_temp, EXPECTED_DECIMAL_PLACES)

    return scaled_temperature, scaled
