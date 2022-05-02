"""Parsers module for AsusRouter"""

from __future__ import annotations

from typing import Any

from asusrouter.util import calculators
from asusrouter.dataclass import Key, ConnectedDevice

from asusrouter.const import(
    AR_DEFAULT_CORES,
    AR_DEFAULT_CORES_RANGE,
    AR_DEVICE_ATTRIBUTES_LIST,
    AR_KEY_CPU_ITEM,
    AR_KEY_CPU_LIST,
    AR_KEY_DEVICE_NAME_LIST,
    AR_KEY_RAM_ITEM,
    AR_KEY_RAM_LIST,
    AR_KEY_NETWORK_ITEM,
    AR_KEY_NETWORK_GROUPS,
    CONST_BITSINBYTE,
    CONST_ZERO,
    DATA_ADD_SPEED,
    DATA_TOTAL,
    DATA_TRAFFIC,
    DEFAULT_TRAFFIC_OVERFLOW,
    KEY_NETWORK,
)


def cpu_cores(raw : dict[str, Any] | None = None) -> list[int]:
    """CPU cores parser"""

    cores = list()

    if raw is None:
        return cores

    for i in AR_DEFAULT_CORES_RANGE:
        if any(AR_KEY_CPU_ITEM.format(i, data_type) in raw for data_type in AR_KEY_CPU_LIST):
            cores.append(i)
        else:
            break

    return cores


def cpu_usage(raw : dict[str, Any], cores : list[int] = AR_DEFAULT_CORES) -> dict[str, Any]:
    """CPU usage parser"""

    cpu = dict()

    # Populate total
    cpu[DATA_TOTAL] = dict()
    for item in AR_KEY_CPU_LIST:
        cpu[DATA_TOTAL][item.get()] = CONST_ZERO

    # Data / core
    for core in cores:
        cpu[core] = dict()

        for item in AR_KEY_CPU_LIST:
            key = AR_KEY_CPU_ITEM.format(core, item)
            new_key = item.get()
            if key in raw:
                cpu[core][new_key] = int(raw[key])
                # Add this to total as well
                cpu[DATA_TOTAL][new_key] += cpu[core][new_key]

    return cpu


def ram_usage(raw : dict[str, Any]) -> dict[str, Any]:
    """RAM usage parser"""

    ram = dict()

    for item in AR_KEY_RAM_LIST:
        if AR_KEY_RAM_ITEM.format(item) in raw:
            ram[item] = int(raw[AR_KEY_RAM_ITEM.format(item)])

    return ram


def network_usage(raw : dict[str, Any], cache : dict[str, Any] | None = None) -> dict[str, Any]:
    """Network usage parser"""

    network = dict()
    for group in AR_KEY_NETWORK_GROUPS:
        for type in DATA_TRAFFIC:
            if AR_KEY_NETWORK_ITEM.format(group, type) in raw:
                if not AR_KEY_NETWORK_GROUPS[group] in network:
                    network[AR_KEY_NETWORK_GROUPS[group]] = dict()
                network[AR_KEY_NETWORK_GROUPS[group]][type] = int(raw[AR_KEY_NETWORK_ITEM.format(group, type)], base = 16)

            elif (cache is not None
                and KEY_NETWORK in cache
                and AR_KEY_NETWORK_GROUPS[group] in cache[DATA_TRAFFIC]
                and type in cache[DATA_TRAFFIC][AR_KEY_NETWORK_GROUPS[group]]
            ):
                network[AR_KEY_NETWORK_GROUPS[group]][type] = cache[DATA_TRAFFIC][AR_KEY_NETWORK_GROUPS[group]][type]

    return network


def network_speed(after : dict[str, dict[str, float]], before : dict[str, dict[str, float]], time_delta : float) -> dict[str, dict[str, float]]:
    """
    Network speed calculator

    Parameters
    -----
    `after`: current values. Outer dictionary `(groups)` contains inner dictionary `(types)`. On each `(type)` calculations are performed

    `before`: previous values

    `time_delta`: time between measurements

    Returns
    -----
    `after` with speeds append to `(types)`
    """

    for group in after:
        if group in before:
            speed = dict()
            for type in after[group]:
                if type in before[group]:
                    speed[DATA_ADD_SPEED.format(type)] = CONST_BITSINBYTE * calculators.speed(after = after[group][type], before = before[group][type], time_delta = time_delta, overflow = DEFAULT_TRAFFIC_OVERFLOW)
                else:
                    speed[DATA_ADD_SPEED.format(type)] = CONST_ZERO
            after[group] |= speed

    return after


def connected_device(raw : dict[str, Any]) -> ConnectedDevice:
    """Device parser"""

    values = dict()

    for key in AR_DEVICE_ATTRIBUTES_LIST:
        if key.value in raw:
            values[key.get()] = key.method(raw[key.value]) if key.method else raw[key.value]

    device = ConnectedDevice(**values)

    return device
