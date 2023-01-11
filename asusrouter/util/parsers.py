"""Parsers module for AsusRouter"""

from __future__ import annotations

import logging
from time import sleep

_LOGGER = logging.getLogger(__name__)

import json
import re
from datetime import datetime, timedelta
from dateutil.parser import parse as dtparse
from typing import Any

import xmltodict

from asusrouter.const import (
    AR_DEFAULT_CORES_RANGE,
    AR_DEFAULT_LEDG,
    AR_DEFAULT_OVPN_CLIENTS,
    AR_DEFAULT_OVPN_SERVERS,
    AR_KEY_CPU_ITEM,
    AR_KEY_CPU_LIST,
    AR_KEY_DEVICEMAP,
    AR_KEY_HEADER,
    AR_KEY_OVPN,
    AR_KEY_OVPN_STATUS,
    AR_KEY_OVPN_STATUS_SERVER,
    AR_KEY_PARENTAL_CONTROL,
    AR_KEY_PARENTAL_CONTROL_MAC,
    AR_KEY_PARENTAL_CONTROL_NAME,
    AR_KEY_PARENTAL_CONTROL_STATE,
    AR_KEY_PARENTAL_CONTROL_TIMEMAP,
    AR_KEY_RAM_ITEM,
    AR_KEY_RAM_LIST,
    AR_KEY_VPN_CLIENT,
    AR_KEY_VPN_SERVER,
    AR_KEY_WAN_STATE,
    AR_MAP_PARENTAL_CONTROL_STATE,
    AR_MAP_RGB,
    AR_MAP_SYSINFO,
    AR_MAP_TEMPERATURE,
    CONST_BITSINBYTE,
    CONST_ZERO,
    CPU,
    DATA_ADD_SPEED,
    DEVICEMAP_BY_INDEX,
    DEVICEMAP_CLEAR,
    DEVICEMAP_GENERAL,
    ENDPOINT,
    ERROR_PARSING,
    ERROR_VALUE,
    ERROR_VALUE_TYPE,
    FIRMWARE,
    MAP_CPU,
    MAP_NETWORK,
    ONBOARDING,
    PARAM_IP,
    PARAM_RIP,
    PARAM_STATE,
    PARAM_STATUS,
    RANGE_CPU_CORES,
    REGEX_VARIABLES,
    SYSINFO,
    TOTAL,
    TRAFFIC_TYPE,
    UPDATE_CLIENTS,
    VALUES_TO_IGNORE,
    VPN,
)
from asusrouter.dataclass import AiMeshDevice, FilterDevice, Firmware
from asusrouter.error import AsusRouterNotImplementedError, AsusRouterValueError
from asusrouter.util import calculators, converters


def cpu_cores(raw: dict[str, Any] | None = None) -> list[int]:
    """CPU cores parser"""

    cores = list()

    if raw is None:
        return cores

    for i in AR_DEFAULT_CORES_RANGE:
        if any(
            AR_KEY_CPU_ITEM.format(i, data_type) in raw for data_type in AR_KEY_CPU_LIST
        ):
            cores.append(i)
        else:
            break

    return cores


def cpu_usage(raw: dict[str, Any]) -> dict[str, Any]:
    """CPU usage parser"""

    cpu = dict()

    # Populate total
    cpu[TOTAL] = dict()
    for item in MAP_CPU:
        cpu[TOTAL][item.get()] = CONST_ZERO

    # Data / core
    for core in RANGE_CPU_CORES:
        if not f"{CPU}{core}_{TOTAL}" in raw:
            break

        cpu[core] = dict()

        for item in MAP_CPU:
            key = f"{CPU}{core}_{item}"
            new_key = item.get()
            if key in raw:
                try:
                    cpu[core][new_key] = int(raw[key])
                except ValueError as ex:
                    raise (AsusRouterValueError(ERROR_VALUE.format(raw[key], str(ex))))
                # Add this to total as well
                cpu[TOTAL][new_key] += cpu[core][new_key]

    return cpu


def ram_usage(raw: dict[str, Any]) -> dict[str, Any]:
    """RAM usage parser"""

    ram = dict()

    for item in AR_KEY_RAM_LIST:
        if AR_KEY_RAM_ITEM.format(item) in raw:
            try:
                ram[item] = int(raw[AR_KEY_RAM_ITEM.format(item)])
            except ValueError as ex:
                raise (
                    AsusRouterValueError(
                        ERROR_VALUE.format(raw[AR_KEY_RAM_ITEM.format(item)], str(ex))
                    )
                )

    return ram


def network_usage(
    raw: dict[str, Any], cache: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Network usage parser"""

    network = dict()
    for interface in MAP_NETWORK:
        data = dict()
        for traffic in TRAFFIC_TYPE:
            try:
                value = converters.int_from_str(
                    raw.get(f"{interface.value}_{traffic}"), base=16
                )
                if value:
                    data[traffic] = value
            except Exception:
                continue
        if len(data) > 0:
            network[interface.get()] = data

    return network


def network_speed(
    after: dict[str, dict[str, float]],
    before: dict[str, dict[str, float]],
    time_delta: float,
) -> dict[str, dict[str, float]]:
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
                    speed[
                        DATA_ADD_SPEED.format(type)
                    ] = CONST_BITSINBYTE * calculators.speed(
                        after=after[group][type],
                        before=before[group][type],
                        time_delta=time_delta,
                    )
                else:
                    speed[DATA_ADD_SPEED.format(type)] = CONST_ZERO
            after[group] |= speed

    return after


def wan_state(raw: dict[str, Any]) -> dict[str, Any]:
    """WAN status parser"""

    values = dict()

    for key in AR_KEY_WAN_STATE:
        if key.value in raw and raw[key.value] != str():
            try:
                values[key.get()] = (
                    key.method(raw[key.value]) if key.method else raw[key.value]
                )
            except AsusRouterValueError as ex:
                _LOGGER.warning(ERROR_PARSING.format(key.value, str(ex)))

    return values


def uptime(data: str) -> datetime:
    """Uptime -> boot time parser"""

    try:
        part = data.split("(")
        seconds = int(re.search("([0-9]+)", part[1]).group())
        when = dtparse(part[0])
        boot = when - timedelta(seconds=seconds)
    except ValueError as ex:
        raise (AsusRouterValueError(ERROR_VALUE.format(data, str(ex))))

    return boot


def port_speed(value: str | None = None) -> int | None:
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
        raise (AsusRouterNotImplementedError(value))


def devicemap(devicemap: dict[str, Any]) -> dict[str, Any]:
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
                if key in devicemap:
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
            data[node][value] = data[node][value].replace(
                DEVICEMAP_CLEAR[node][value], ""
            )

    return data


def ledg_count(raw: str) -> int:
    """LEDG count parser"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))
    if raw.strip() == str():
        return {}

    value = re.search("ledg_count: ([0-9]+)", raw)
    if value:
        count = int(value[1])
    else:
        count = 0

    return count


def temperatures(raw: str) -> dict[str, Any]:
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


def rgb(raw: str, num: int = AR_DEFAULT_LEDG) -> dict[int, dict[str, int]]:
    """RGB to channels parser"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))
    if raw.strip() == str():
        return {}

    leds = dict()

    color = re.findall("([0-9]+)", raw)
    length = len(color)

    for led in range(1, num):
        ind = (led - 1) * 3
        if ind + 2 > length:
            break
        if not led in leds:
            leds[led] = dict()
        for channel in AR_MAP_RGB:
            leds[led][AR_MAP_RGB[channel]] = color[ind + channel]

    return leds


def sysinfo(raw: str) -> dict[str, Any]:
    """Sysinfo parser"""

    raw = raw.replace("=", '":')
    raw = raw.replace(";", ',"')
    raw = '{"' + raw[:-2] + "}"
    data = json.loads(raw)

    result = dict()

    for set in AR_MAP_SYSINFO:
        if set in data:
            for key in AR_MAP_SYSINFO[set]:
                try:
                    result[key.get()] = (
                        key.method(data[set][key.value])
                        if key.method
                        else data[set][key.value]
                    )
                except AsusRouterValueError as ex:
                    _LOGGER.warning(ERROR_PARSING.format(key.value, str(ex)))

    return result


def onboarding(raw: str) -> dict[str, Any]:
    """Onboarding parser"""

    raw = raw.replace("\ufeff", "")
    raw = raw.replace("=", '":')
    raw = raw.replace(";", ',"')
    raw = raw.replace("[0]", "")
    raw = '{"' + raw[:-2] + "}"
    data = json.loads(raw)

    result = dict()

    return data


def aimesh_node(raw: dict[str, Any]) -> AiMeshDevice:
    """AiMesh node parser"""

    AP = {
        "2g": "2ghz",
        "5g": "5ghz",
        "5g1": "5ghz2",
        "6g": "6ghz",
        "dwb": "dwb",
    }

    FREQUENCIES = [
        "2g",
        "5g",
        "6g",
    ]

    ap = dict()
    for el in AP:
        if f"ap{el}" in raw and raw[f"ap{el}"] is not str():
            ap[AP[el]] = raw[f"ap{el}"]

    parent = dict()
    for el in FREQUENCIES:
        if f"pap{el}" in raw and raw[f"pap{el}"] is not str():
            parent["connection"] = AP[el]
            parent["mac"] = raw[f"pap{el}"]
            parent["rssi"] = converters.none_or_str(raw.get(f"rssi{el}"))
            parent["ssid"] = converters.none_or_str(raw.get(f"pap{el}_ssid"))

    level = converters.int_from_str(raw.get("level", "0"))
    state = "router" if level == 0 else "node"

    return AiMeshDevice(
        status=converters.bool_from_any(raw.get("online", 0)),
        alias=raw.get("alias", None),
        model=raw.get("ui_model_name", raw.get("model_name", None)),
        product_id=raw.get("product_id"),
        ip=raw.get("ip"),
        fw=raw.get("fwver", None),
        fw_new=converters.none_or_str(raw.get("newfwver")),
        mac=raw.get("mac", None),
        ap=ap,
        parent=parent,
        state=state,
        level=level,
        config=raw.get("config"),
    )


def parental_control(raw: dict[str, Any]) -> dict[str, Any]:
    """Parental control parser"""

    result = dict()

    result[AR_KEY_PARENTAL_CONTROL.get()] = AR_KEY_PARENTAL_CONTROL.method(
        raw[AR_KEY_PARENTAL_CONTROL.value]
    )

    # If no rules are set
    if raw.get(AR_KEY_PARENTAL_CONTROL_MAC) == raw.get(AR_KEY_PARENTAL_CONTROL_STATE):
        result["list"] = dict()
        return result

    list = dict()

    for el in raw:
        raw[el] = raw[el].split("&#62")

    size = len(raw["MULTIFILTER_MAC"])

    for i in range(0, size):
        device = FilterDevice(
            mac=raw[AR_KEY_PARENTAL_CONTROL_MAC][i],
            name=raw[AR_KEY_PARENTAL_CONTROL_NAME][i],
            state=AR_MAP_PARENTAL_CONTROL_STATE.get(
                raw[AR_KEY_PARENTAL_CONTROL_STATE][i], None
            ),
            timemap=raw[AR_KEY_PARENTAL_CONTROL_TIMEMAP][i]
            if i < len(raw[AR_KEY_PARENTAL_CONTROL_TIMEMAP])
            else "",
        )
        list[raw[AR_KEY_PARENTAL_CONTROL_MAC][i]] = device

    result["list"] = list.copy()

    return result


def endpoint_update_clients(raw: str) -> dict[str, Any]:
    """Parse data from the `update_clients` endpoint"""

    parts = raw.split("originData =")
    parts = parts[1].split("networkmap_fullscan")
    data = (
        parts[0]
        .replace("fromNetworkmapd", '"fromNetworkmapd"')
        .replace("nmpClient ", '"nmpClient" ')
    )
    return json.loads(data.encode().decode("utf-8-sig"))


def pseudo_json(text: str, page: str) -> dict[str, Any]:
    """JSON parser"""

    if ENDPOINT[VPN] in page:
        return vpn_status(text)
    if ENDPOINT[FIRMWARE] in page:
        return firmware(text)
    if ENDPOINT[UPDATE_CLIENTS] in page:
        return endpoint_update_clients(text)

    data = re.sub("\s+", "", text)

    if "curr_coreTmp" in data:
        return temperatures(data)
    # Merlin
    elif ENDPOINT[SYSINFO] in page:
        return sysinfo(data)
    elif ENDPOINT[ONBOARDING] in page:
        return onboarding(data)
    elif "get_clientlist" in data:
        data = data.replace('"get_clientlist":', '"get_clientlist":{')
        data += "}"
    elif "get_wan_lan_status=" in data:
        data = data.replace("get_wan_lan_status=", "")
        data = data[:-1]
    elif "varcpuInfo,memInfo=newObject();cpuInfo=" in data:
        data = data.replace("varcpuInfo,memInfo=newObject();cpuInfo=", '{"cpu":{')
        data = data.replace(";memInfo=", '},"memory":{')
        data = data.replace(";", "}}")
    else:
        _LOGGER.error("Unknown data. Template for this data is unknown")
        return {}

    return json.loads(data.encode().decode("utf-8-sig"))


def xml(text: str, page: str) -> dict[str, Any]:
    """XML parser"""

    data = xmltodict.parse(text)
    if AR_KEY_DEVICEMAP in data:
        return devicemap(data[AR_KEY_DEVICEMAP])

    return {}


def ovpn_client_status(raw: str) -> dict[str, Any]:
    """OpenVPN client status parser"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))
    raw = raw.strip()
    if raw == str() or raw == "None":
        return {}

    values = dict()

    for key in AR_KEY_OVPN_STATUS:
        if key.value in raw:
            value = re.search(f"{key.value},(.*?)(?=>)", raw)
            if value:
                values[key.get()] = key.method(value[1]) if key.method else value[1]

    return values


def ovpn_server_status(raw: str) -> dict[str, Any]:
    """OpenVPN server status parser"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))
    raw = raw.strip()
    if raw == str() or raw == "None":
        return {}

    values = dict()

    for key in AR_KEY_OVPN_STATUS_SERVER:
        if key.value in raw:
            flag = False
            # Find headers
            header = re.search(f"{AR_KEY_HEADER},{key.value},(.*?)(?=>)", raw)
            if header:
                keys_raw = header[1].split(",")
                keys = list()
                for el in keys_raw:
                    keys.append(converters.to_snake_case(el))
                flag = True

            # Hide header
            raw = raw.replace(f"{AR_KEY_HEADER},{key.value},", "USED-")

            values[key.get()] = list()
            # Find values
            while value := re.search(f"{key.value},(.*?)(?=>)", raw):
                if not value:
                    break
                if flag:
                    cut = value[1].split(",")
                    i = 0
                    set = dict()
                    while i < len(cut) and i < len(keys):
                        set[keys[i]] = cut[i]
                        i += 1
                    values[key.get()].append(set.copy())
                else:
                    if key.method:
                        values[key.get()].append(key.method(value[1]))
                    else:
                        values[key.get()].append(value[1])
                raw = raw.replace(f"{key.value},{value[1]}", "USED-")

    return values


# var = "value";
def variables(raw: str) -> dict[str, Any]:
    """Variables parser"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))
    if raw.strip() == str():
        return {}

    values = dict()
    temp = raw
    while len(temp) > 0:
        value = re.search(REGEX_VARIABLES, temp)
        if not value:
            break
        values[value[1]] = value[2]
        temp = temp.replace(f"{value[0]};", "")

    return values


def firmware(raw: str) -> dict[str, Any]:
    """Firmware parser"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))
    if raw.strip() == str():
        return {}

    values = variables(raw.replace("'", '"'))

    return values


def firmware_string(raw: str) -> Firmware:
    """Firmware string parser"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))

    string = re.match(
        "^(3.?0.?0.?4)?[_.]?([0-9]{3})[_.]?([0-9]+)[_.-]?([a-zA-Z0-9-_]+)?$", raw
    )
    if not string:
        _LOGGER.warning(
            f"Firmware version cannot be parser. Please report this. The original FW string is: {raw}"
        )
        return Firmware()

    major = string[1]
    if major and not "." in major and len(major) == 4:
        major = major[0] + "." + major[1] + "." + major[2] + "." + major[3]

    minor = int(string[2])
    build = int(string[3])
    if string[4] and string[4].isdigit():
        build_more = int(string[4])
    else:
        build_more = string[4]

    fw = Firmware(
        minor=minor,
        build=build,
        build_more=build_more,
    )
    if major:
        fw.major = major

    return fw


def vpn_status(raw: str) -> dict[str, Any]:
    """VPN status parser"""

    if type(raw) != str:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(raw, type(raw)))
    if raw.strip() == str():
        return {}

    vpns = dict()

    values = variables(raw)

    # Clients
    for num in range(1, AR_DEFAULT_OVPN_CLIENTS + 1):
        key = AR_KEY_OVPN.format(AR_KEY_VPN_CLIENT, num, PARAM_STATUS)
        if not key in values:
            break

        vpn_id = AR_KEY_VPN_CLIENT + str(num)

        if values[key] not in VALUES_TO_IGNORE:
            vpns[vpn_id] = ovpn_client_status(values[key])
            vpns[vpn_id][PARAM_STATE] = True
        else:
            vpns[vpn_id] = dict()
            vpns[vpn_id][PARAM_STATE] = False

        key = AR_KEY_OVPN.format(AR_KEY_VPN_CLIENT, num, PARAM_IP)
        if key in values and values[key] not in VALUES_TO_IGNORE:
            vpns[vpn_id][PARAM_IP] = values[key]

        key = AR_KEY_OVPN.format(AR_KEY_VPN_CLIENT, num, PARAM_RIP)
        if key in values and values[key] not in VALUES_TO_IGNORE:
            vpns[vpn_id][PARAM_RIP] = values[key]

    # Servers
    for num in range(1, AR_DEFAULT_OVPN_SERVERS + 1):
        key = AR_KEY_OVPN.format(AR_KEY_VPN_SERVER, num, PARAM_STATUS)
        if not key in values:
            break

        vpn_id = AR_KEY_VPN_SERVER + str(num)

        if values[key] not in VALUES_TO_IGNORE:
            vpns[vpn_id] = ovpn_server_status(values[key])
            vpns[vpn_id][PARAM_STATE] = True
        else:
            vpns[vpn_id] = dict()
            vpns[vpn_id][PARAM_STATE] = False

        key = AR_KEY_OVPN.format(AR_KEY_VPN_SERVER, num, PARAM_IP)
        if key in values and values[key] not in VALUES_TO_IGNORE:
            vpns[vpn_id][PARAM_IP] = values[key]

        key = AR_KEY_OVPN.format(AR_KEY_VPN_SERVER, num, PARAM_RIP)
        if key in values and values[key] not in VALUES_TO_IGNORE:
            vpns[vpn_id][PARAM_RIP] = values[key]

    return vpns
