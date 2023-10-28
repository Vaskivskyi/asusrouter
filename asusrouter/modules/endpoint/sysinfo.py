"""SysInfo endpoint module."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.data import AsusData
from asusrouter.modules.wlan import WLAN_TYPE, Wlan
from asusrouter.tools.cleaners import clean_content
from asusrouter.tools.converters import safe_float, safe_int
from asusrouter.tools.readers import read_json_content


def read(content: str) -> dict[str, Any]:
    """Read sysinfo data"""

    # Prepare the content
    content = clean_content(content).replace(" = ", '":').replace(";\n", ',"')
    content = '{"' + content[:-3] + "}"

    # Read the json content
    sysinfo: dict[str, Any] = read_json_content(content)

    return sysinfo


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process sysinfo data"""

    state: dict[AsusData, Any] = {}

    sysinfo = {}

    # WLAN info
    wlan_info = {}
    i = 0
    while wlan_data := data.get(f"wlc_{i}_arr"):
        name = WLAN_TYPE.get(i, Wlan.UNKNOWN)
        wlan_info[name] = {
            "client_associated": safe_int(wlan_data[0]),
            "client_authorized": safe_int(wlan_data[1]),
            "client_authenticated": safe_int(wlan_data[2]),
        }
        i += 1
    sysinfo["wlan"] = wlan_info

    # Connections info
    connections_info = {}
    connections_data = data.get("conn_stats_arr")
    if connections_data:
        connections_info = {
            "total": safe_int(connections_data[0]),
            "active": safe_int(connections_data[1]),
        }
    sysinfo["connections"] = connections_info

    # Memory info
    memory_info = {}
    memory_data = data.get("mem_stats_arr")
    if memory_data:
        # JFFS data is presented as a string of `XX.xx / YY.yy MB`
        # where `XX.xx` is the used space (float) and `YY.yy` is the total space (float)
        jffs_data = memory_data[7][:-3].split(" / ")
        jffs_used = safe_float(jffs_data[0])
        jffs_total = safe_float(jffs_data[1])

        memory_info = {
            "total": safe_float(memory_data[0]),
            "free": safe_float(memory_data[1]),
            "buffers": safe_float(memory_data[2]),
            "cache": safe_float(memory_data[3]),
            "swap_1": safe_float(memory_data[4]),
            "swap_2": safe_float(memory_data[5]),
            "nvram": safe_int(memory_data[6]),
            "jffs_used": jffs_used,
            "jffs_total": jffs_total,
        }
    sysinfo["memory"] = memory_info

    # Load average info
    load_avg_info = {}
    load_avg_data = data.get("cpu_stats_arr")
    if load_avg_data:
        load_avg_info = {
            1: safe_float(load_avg_data[0]),
            5: safe_float(load_avg_data[1]),
            15: safe_float(load_avg_data[2]),
        }
    sysinfo["load_avg"] = load_avg_info

    # Sysinfo as it is
    state[AsusData.SYSINFO] = sysinfo

    return state
