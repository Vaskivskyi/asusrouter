"""Temperature endpoint module."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.data import AsusData
from asusrouter.modules.wlan import Wlan
from asusrouter.tools.cleaners import clean_content
from asusrouter.tools.converters import safe_float
from asusrouter.tools.readers import read_js_variables


# The temperature data can be presented it the following JS variables:
# 1) curr_coreTmp_2_raw, curr_coreTmp_5_raw, curr_coreTmp_52_raw
# 2) curr_coreTmp_0_raw, curr_coreTmp_1_raw, curr_coreTmp_2_raw, curr_coreTmp_3_raw
# 3) curr_coreTmp_wl0_raw, curr_coreTmp_wl1_raw, curr_coreTmp_wl2_raw, curr_coreTmp_wl3_raw
# for 2ghz, 5ghz, 5ghz2, 6ghz respectively
# CPU temperature is set either in curr_cpuTemp or curr_coreTmp_cpu
def read(content: str) -> dict[str, Any]:
    """Read temperature data."""

    temperature: dict[str, Any] = {}

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

    # Convert the temperature values to float or remove them if they have "disabled"
    temperature = {
        key: safe_float(value)
        for key, value in temperature.items()
        if value and "disabled" not in value
    }

    return temperature


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process temperature data."""

    temperature: dict[AsusData, Any] = {
        AsusData.TEMPERATURE: data,
    }

    return temperature
