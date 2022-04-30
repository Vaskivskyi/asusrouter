"""Helpers module"""

from __future__ import annotations

import json
import logging
import re
import xmltodict
from datetime import datetime, timedelta

from .const import (
    DEVICEMAP_BY_INDEX,
    DEVICEMAP_CLEAR,
    DEVICEMAP_GENERAL,
    DEVICEMAP_SPECIAL,
)

_LOGGER = logging.getLogger(__name__)


async def async_convert_to_json(text : str) -> dict:
    """Fix JSON conversion for known pages"""

    data = re.sub('\s+','',text)

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

async def async_convert_xml(text : str) -> dict:
    """Obtain data from XML"""

    data = xmltodict.parse(text)
    if 'devicemap' in data:
        return await async_parse_devicemap(data['devicemap'])

    return {}

async def async_parse_devicemap(devicemap : dict) -> dict:
    """Parse devicemap"""

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

async def async_parse_uptime(data : str) -> datetime:
    """Parse uptime to get boot time"""

    part = data.split("(")
    seconds = int(re.search("([0-9]+)", part[1]).group())
    when = datetime.strptime(part[0], "%a, %d %b %Y %H:%M:%S %z")

    boot = when - timedelta(seconds = seconds)

    return boot


async def async_transform_port_speed(value : str | None = None) -> int | None:
    """Transform port speed from the text value to actual speed in Mb/s"""

    if value is None:
        return None
    elif value == "X":
        return 0
    elif value == "M":
        return 100
    elif value == "G":
        return 1000
    else:
        raise NotImplementedError("Conversion for this value is not implemented")

async def async_transform_connection_time(value : str | None = None) -> datetime:
    """Transform connection timedelta of the device to a proper datetime object when the device was connected"""

    if value is None:
        return None

    part = value.split(":")
    delta = timedelta(hours = int(part[0]), minutes = int(part[1]), seconds = int(part[2]))
    return datetime.utcnow().replace(microsecond=0) - delta

