"""Parsers module for AsusRouter"""

from __future__ import annotations

import logging
_LOGGER = logging.getLogger(__name__)

from typing import Any
import re
from datetime import datetime, timedelta
import xmltodict
import json

from asusrouter.const import(
    AR_DEFAULT_CORES,
    AR_DEFAULT_CORES_RANGE,
    AR_DEVICE_ATTRIBUTES_LIST,
    AR_KEY_CPU_ITEM,
    AR_KEY_CPU_LIST,
    AR_KEY_DEVICEMAP,
    AR_KEY_RAM_ITEM,
    AR_KEY_RAM_LIST,
    AR_KEY_NETWORK_ITEM,
    AR_KEY_NETWORK_GROUPS,
    AR_KEY_WAN_STATE,
    AR_MAP_TEMPERATURE,
    CONST_BITSINBYTE,
    CONST_ZERO,
    DATA_ADD_SPEED,
    DATA_TOTAL,
    DATA_TRAFFIC,
    DEFAULT_TRAFFIC_OVERFLOW,
    DEVICEMAP_BY_INDEX,
    DEVICEMAP_CLEAR,
    DEVICEMAP_GENERAL,
    ERROR_PARSING,
    ERROR_VALUE,
    ERROR_VALUE_TYPE,
    KEY_NETWORK,
)
from asusrouter.dataclass import ConnectedDevice
from asusrouter.error import AsusRouterNotImplementedError, AsusRouterValueError
from asusrouter.util import calculators



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
                try:
                    cpu[core][new_key] = int(raw[key])
                except ValueError as ex:
                    raise(AsusRouterValueError(ERROR_VALUE.format(raw[key], str(ex))))
                # Add this to total as well
                cpu[DATA_TOTAL][new_key] += cpu[core][new_key]

    return cpu


def ram_usage(raw : dict[str, Any]) -> dict[str, Any]:
    """RAM usage parser"""

    ram = dict()

    for item in AR_KEY_RAM_LIST:
        if AR_KEY_RAM_ITEM.format(item) in raw:
            try:
                ram[item] = int(raw[AR_KEY_RAM_ITEM.format(item)])
            except ValueError as ex:
                raise(AsusRouterValueError(ERROR_VALUE.format(raw[AR_KEY_RAM_ITEM.format(item)], str(ex))))

    return ram


def network_usage(raw : dict[str, Any], cache : dict[str, Any] | None = None) -> dict[str, Any]:
    """Network usage parser"""

    network = dict()
    for group in AR_KEY_NETWORK_GROUPS:
        for type in DATA_TRAFFIC:
            if AR_KEY_NETWORK_ITEM.format(group, type) in raw:
                if not AR_KEY_NETWORK_GROUPS[group] in network:
                    network[AR_KEY_NETWORK_GROUPS[group]] = dict()
                try:
                    network[AR_KEY_NETWORK_GROUPS[group]][type] = int(raw[AR_KEY_NETWORK_ITEM.format(group, type)], base = 16)
                except ValueError as ex:
                    raise(AsusRouterValueError(ERROR_VALUE.format(raw[AR_KEY_NETWORK_ITEM.format(group, type)], str(ex))))

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


def wan_state(raw : dict[str, Any]) -> dict[str, Any]:
    """WAN status parser"""

    values = dict()

    for key in AR_KEY_WAN_STATE:
        if (key.value in raw
            and raw[key.value] != str()
        ):
            try:
                values[key.get()] = key.method(raw[key.value]) if key.method else raw[key.value]
            except AsusRouterValueError as ex:
                _LOGGER.warning(ERROR_PARSING.format(key.value, str(ex)))

    return values


def connected_device(raw : dict[str, Any]) -> ConnectedDevice:
    """Device parser"""

    values = dict()

    for key in AR_DEVICE_ATTRIBUTES_LIST:
        if (key.value in raw
            and raw[key.value] != str()
        ):
            try:
                values[key.get()] = key.method(raw[key.value]) if key.method else raw[key.value]
            except AsusRouterValueError as ex:
                _LOGGER.warning(ERROR_PARSING.format(key.value, str(ex)))

    device = ConnectedDevice(**values)

    return device


def uptime(data : str) -> datetime:
    """Uptime -> boot time parser"""

    try:
        part = data.split("(")
        seconds = int(re.search("([0-9]+)", part[1]).group())
        when = datetime.strptime(part[0], "%a, %d %b %Y %H:%M:%S %z")
        boot = when - timedelta(seconds = seconds)
    except ValueError as ex:
        raise(AsusRouterValueError(ERROR_VALUE.format(data, str(ex))))

    return boot


def port_speed(value : str | None = None) -> int | None:
    """Port speed -> Mb/s parcer"""

    if value is None:
        return None
    elif value == "X":
        return 0
    elif value == "M":
        return 100
    elif value == "G":
        return 1000
    elif value == "Q":
        return 2500
    else:
        raise(AsusRouterNotImplementedError(value))


def devicemap(devicemap : dict[str, Any]) -> dict[str, Any]:
    """Devicemap parser"""

    data = {}

    # Get values only with index
    for node in DEVICEMAP_BY_INDEX:
        _node = {}
        for key in DEVICEMAP_BY_INDEX[node]:
            for el in range(len(DEVICEMAP_BY_INDEX[node][key])):
                _node[DEVICEMAP_BY_INDEX[node][key][el]] = devicemap[key][el]
            del devicemap[key][0 : (len(DEVICEMAP_BY_INDEX[node][key]) - 1)]
        data[node] = _node

    # Get values by key
    for node in DEVICEMAP_GENERAL:
        _node = {}
        for key in DEVICEMAP_GENERAL[node]:
            for el in DEVICEMAP_GENERAL[node][key]:
                if type(devicemap[key]) == str:
                    if el in devicemap[key]:
                        _node[el] = devicemap[key].replace("{}=".format(el), "")
                        break
                else:
                    for value in devicemap[key]:
                        if el in value:
                            _node[el] = value.replace("{}=".format(el), "")
                            break
        if node in data:
            data[node].update(_node)
        else:
            data[node] = _node

    # Clear values from useless symbols
    for node in DEVICEMAP_CLEAR:
        for value in DEVICEMAP_CLEAR[node]:
            data[node][value] = data[node][value].replace(DEVICEMAP_CLEAR[node][value], "")

    return data


def temperatures(raw : str) -> dict[str, Any]:
    """Temperature parser"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))
    if raw.strip() == str():
        return {}

    temp = dict()

    for sensor in AR_MAP_TEMPERATURE:
        for reg in AR_MAP_TEMPERATURE[sensor]:
            value = re.search(reg, raw)
            if value:
                temp[sensor] = float(value[1])

    return temp


def pseudo_json(text : str) -> dict[str, Any]:
    """JSON parser"""

    data = re.sub('\s+','',text)

    if "curr_coreTmp" in data:
        return temperatures(data)

    if "get_wan_lan_status=" in data:
        data = data.replace("get_wan_lan_status=", "")
        data = data[:-1]
    elif "varcpuInfo,memInfo=newObject();cpuInfo=" in data:
        data = data.replace("varcpuInfo,memInfo=newObject();cpuInfo=", '{"cpu":{')
        data = data.replace(";memInfo=", '},"memory":{')
        data = data.replace(";", "}}")
    else:
        _LOGGER.error("Unknown data. Template for this data is unknown")
        return {}
    
    return json.loads(data.encode().decode('utf-8-sig') )


def xml(text : str) -> dict[str, Any]:
    """XML parser"""

    data = xmltodict.parse(text)
    if AR_KEY_DEVICEMAP in data:
        return devicemap(data[AR_KEY_DEVICEMAP])

    return {}


