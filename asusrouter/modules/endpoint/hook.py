"""Hook endpoint module."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from asusrouter.modules.connection import ConnectionState
from asusrouter.modules.data import AsusData, AsusDataState
from asusrouter.modules.endpoint import data_get
from asusrouter.modules.led import AsusLED
from asusrouter.modules.parental_control import (
    KEY_PARENTAL_CONTROL_MAC,
    KEY_PARENTAL_CONTROL_STATE,
    KEY_PARENTAL_CONTROL_TYPE,
    MAP_PARENTAL_CONTROL_ITEM,
    MAP_PARENTAL_CONTROL_TYPE,
    AsusParentalControl,
    ParentalControlRule,
)
from asusrouter.modules.port_forwarding import (
    KEY_PORT_FORWARDING_LIST,
    KEY_PORT_FORWARDING_STATE,
    AsusPortForwarding,
    PortForwardingRule,
)
from asusrouter.modules.wlan import MAP_GWLAN, MAP_WLAN, Wlan
from asusrouter.tools.converters import (
    run_method,
    safe_int,
    safe_return,
    safe_speed,
    safe_unpack_key,
    safe_unpack_keys,
    safe_usage,
    safe_usage_historic,
)
from asusrouter.tools.readers import read_json_content

from .hook_const import MAP_NETWORK, MAP_WAN, MAP_WIREGUARD, MAP_WIREGUARD_CLIENT

REQUIRE_HISTORY = True
REQUIRE_WLAN = True


def read(content: str) -> dict[str, Any]:
    """Read hook data"""

    hook: dict[str, Any] = read_json_content(content)

    return hook


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process hook data."""

    # For this endpoint, the received data always depends on the sent request.
    # So, we need to check which data is available and process it accordingly.
    # Otherwise, we can accidentally overwrite the data with empty values.

    state: dict[AsusData, Any] = {}

    # Get the passed awrguments
    history: dict[AsusData, AsusDataState] = data_get(data, "history") or {}
    wlan = data_get(data, "wlan") or []

    # CPU
    if "cpu_usage" in data:
        cpu_usage = data.get("cpu_usage", {})
        prev_cpu: Optional[AsusDataState] = history.get(AsusData.CPU)
        state[AsusData.CPU] = (
            process_cpu(cpu_usage, prev_cpu)
            if cpu_usage
            else prev_cpu.data
            if isinstance(prev_cpu, AsusDataState)
            else {}
        )

    # GWLAN
    if (
        "wl0.1_wpa_psk" in data
        or "wl1.1_wpa_psk" in data
        or "wl2.1_wpa_psk" in data
        or "wl3.1_wpa_psk" in data
    ):
        state[AsusData.GWLAN] = process_gwlan(data, wlan)

    # LED
    if "led_val" in data:
        state[AsusData.LED] = {
            "state": AsusLED(safe_int(data.get("led_val"), default=-999))
        }

    # Network
    if "netdev" in data:
        prev_network: Optional[AsusDataState] = history.get(AsusData.NETWORK)
        netdev = data.get("netdev")
        state[AsusData.NETWORK] = (
            process_network(netdev, prev_network)
            if netdev
            else prev_network.data
            if isinstance(prev_network, AsusDataState)
            else {}
        )

    # Parental control
    if KEY_PARENTAL_CONTROL_STATE in data:
        state[AsusData.PARENTAL_CONTROL] = process_parental_control(data)

    # Port forwarding
    if KEY_PORT_FORWARDING_STATE in data:
        state[AsusData.PORT_FORWARDING] = process_port_forwarding(data)

    # RAM
    if "memory_usage" in data:
        memory_usage = data.get("memory_usage", {})
        state[AsusData.RAM] = process_ram(memory_usage) if memory_usage else {}

    # WAN
    if "wanlink_state" in data:
        wanlink_state = data.get("wanlink_state", {})
        state[AsusData.WAN] = process_wan(wanlink_state) if wanlink_state else {}

    # WireGuard
    if "get_wgsc_status" in data:
        state[AsusData.WIREGUARD] = process_wireguard(data)

    # WLAN
    if (
        "wl0_wpa_psk" in data
        or "wl1_wpa_psk" in data
        or "wl2_wpa_psk" in data
        or "wl3_wpa_psk" in data
    ):
        state[AsusData.WLAN] = process_wlan(data, wlan)

    return state


def process_cpu(
    cpu_usage: dict[str, Any], history: Optional[AsusDataState]
) -> dict[str | int, Any]:
    """Process CPU data."""

    cpu = process_cpu_usage(cpu_usage)

    # Get the previous data
    prev_cpu = history.data if history else None

    # Safe calculate of actual usage if previous data is available
    if prev_cpu:
        for item, after in cpu.items():
            if item in prev_cpu:
                before = prev_cpu[item]
                after["usage"] = safe_usage_historic(
                    after["used"], after["total"], before["used"], before["total"]
                )

    return cpu


def process_cpu_usage(raw: dict[str, Any]) -> dict[str | int, Any]:
    """Process CPU usage."""

    # Populate total
    cpu: dict[str | int, Any] = {"total": {"total": 0.0, "used": 0.0}}

    # Process each core
    core = 1
    while f"cpu{core}_total" in raw:
        cpu[core] = {
            "total": int(raw[f"cpu{core}_total"]),
            "used": int(raw[f"cpu{core}_usage"]),
        }
        # Update the total
        cpu["total"]["total"] += cpu[core]["total"]
        cpu["total"]["used"] += cpu[core]["used"]

        core += 1

    return cpu


def process_gwlan(data: dict[str, Any], wlan_list: list[Wlan]) -> dict[str, Any]:
    """Process GWLAN data."""

    gwlan = {}

    for interface in wlan_list:
        index = list(Wlan).index(interface)
        for gid in range(1, 4):
            info = {}
            for pair in MAP_GWLAN:
                key, method = safe_unpack_key(pair)
                info[key.format(f"{index}.{gid}")[6:]] = (
                    method(data.get(key.format(f"{index}.{gid}")))
                    if method
                    else data.get(key.format(f"{index}.{gid}"))
                )
            gwlan[f"{interface.value}_{gid}"] = info

    return gwlan


def process_network(
    netdev: dict[str, Any], history: Optional[AsusDataState]
) -> dict[str, Any]:
    """Process network data."""

    # Calculate RX and TX from the HEX values.
    network = process_network_usage(netdev)

    # Calculate speeds if previous data is available
    if history and history.data:
        time_delta = (datetime.now(timezone.utc) - history.timestamp).total_seconds()
        network = process_network_speed(network, history.data, time_delta)

    return network


def process_network_speed(
    network: dict[str, dict[str, float]],
    prev_network: dict[str, dict[str, float]],
    time_delta: float | None,
) -> dict[str, dict[str, float]]:
    """Calculate network speed for a set period of time"""

    # Check values one by one
    for interface in network:
        # Skip if there is no previous data
        if interface not in prev_network:
            continue

        # Dictionary with speed values
        interface_speed = {}

        # Calculate speed for each traffic type
        for traffic_type, traffic_value in network[interface].items():
            prev_traffic_value = prev_network[interface].get(traffic_type)
            # Calculate speed only if previous value is available
            if prev_traffic_value:
                interface_speed[f"{traffic_type}_speed"] = 8 * safe_speed(
                    traffic_value,
                    prev_traffic_value,
                    time_delta,
                )
                continue
            # Otherwise, set speed to 0
            interface_speed[f"{traffic_type}_speed"] = 0.0

        # Update interface with speed values
        network[interface].update(interface_speed)

    return network


def process_network_usage(raw: dict[str, Any]) -> dict[str, Any]:
    """Process network usage data"""

    network = {}
    for key, key_to_use in MAP_NETWORK.items():
        data = {}
        for traffic_type in ("rx", "tx"):
            # Convert string with HEX value to int
            value = safe_int(raw.get(f"{key}_{traffic_type}"), base=16)
            # Check that value is integer
            if isinstance(value, int):
                data[traffic_type] = value
        if len(data) > 0:
            network[key_to_use] = data

    return network


def process_parental_control(data: dict[str, Any]) -> dict[str, Any]:
    """Process parental control data"""

    parental_control: dict[str, Any] = {}

    # State
    parental_control["state"] = AsusParentalControl(
        safe_int(data.get(KEY_PARENTAL_CONTROL_STATE), default=-999)
    )

    # Rules
    rules = {}

    if data.get(KEY_PARENTAL_CONTROL_MAC) != data.get(KEY_PARENTAL_CONTROL_TYPE):
        as_is = {
            key_to_use: [
                method(temp_element) for temp_element in data[key].split("&#62")
            ]
            for key, key_to_use, method in MAP_PARENTAL_CONTROL_ITEM
        }

        number = len(as_is["mac"])
        for i in range(number):
            rules[as_is["mac"][i]] = ParentalControlRule(
                mac=as_is["mac"][i],
                name=as_is["name"][i],
                type=MAP_PARENTAL_CONTROL_TYPE.get(as_is["type"][i], "unknown"),
                timemap=as_is["timemap"][i] if i < len(as_is["timemap"]) else None,
            )

    parental_control["rules"] = rules.copy()

    return parental_control


def process_port_forwarding(data: dict[str, Any]) -> dict[str, Any]:
    """Process port forwarding data."""

    port_forwarding = {}

    # State
    port_forwarding["state"] = AsusPortForwarding(
        safe_int(data.get(KEY_PORT_FORWARDING_STATE), default=-999)
    )

    # Rules
    pf_list = data.get(KEY_PORT_FORWARDING_LIST)
    if pf_list:
        rules = []
        rule_list = pf_list.split("&#60")
        for rule in rule_list:
            if rule == str():
                continue
            part = rule.split("&#62")
            rules.append(
                PortForwardingRule(
                    name=safe_return(part[0]),
                    ip_address=part[2],
                    port=safe_return(part[3]),
                    protocol=part[4],
                    ip_external=safe_return(part[5]),
                    port_external=part[1],
                )
            )
        port_forwarding["rules"] = rules.copy()

    return port_forwarding


def process_ram(memory_usage: dict[str, Any]) -> dict[str, Any]:
    """Process RAM data."""

    ram: dict[str, Any] = {}
    # Data is in KiB. To get MB as they are shown in the device Web-GUI,
    # should be devided by 1024 (yes, those will be MiB)

    # Populate RAM with known values
    ram = {
        "free": int(memory_usage["mem_free"]),
        "total": int(memory_usage["mem_total"]),
        "used": int(memory_usage["mem_used"]),
    }
    # Calculate usage in percents
    if "used" in ram and "total" in ram:
        ram["usage"] = safe_usage(ram["used"], ram["total"])

    return ram


def process_wan(wanlink_state: dict[str, Any]) -> dict[str, Any]:
    """Process WAN data."""

    wan = {}

    for keys in MAP_WAN:
        key, key_to_use, method = safe_unpack_keys(keys)
        state_value = wanlink_state.get(key)
        if state_value:
            wan[key_to_use] = run_method(state_value, method)

    return wan


def process_wireguard(data: dict[str, Any]) -> dict[str, Any]:
    """Process WireGuard data."""

    wireguard = {}

    # Server data
    for keys in MAP_WIREGUARD:
        key, key_to_use, method = safe_unpack_keys(keys)
        state_value = data.get(key)
        if state_value:
            wireguard[key_to_use] = run_method(state_value, method)

    # Per-client data
    wireguard["clients"] = {}
    for num in range(1, 11):
        client = {}
        for keys in MAP_WIREGUARD_CLIENT:
            key, key_to_use, method = safe_unpack_keys(keys)
            state_value = data.get(f"wgs1_c{num}_{key}")
            if state_value:
                client[key_to_use] = run_method(state_value, method)
        if client:
            wireguard["clients"][num] = client

    if "status" in wireguard:
        status = wireguard["status"].get("client_status")
        if status:
            for client in status:
                if client.get("index") in wireguard["clients"]:
                    wireguard["clients"][client.get("index")][
                        "state"
                    ] = ConnectionState(client.get("status"))

    # Remove the `status` value
    wireguard.pop("status")

    return wireguard


def process_wlan(data: dict[str, Any], wlan_list: list[Wlan]) -> dict[str, Any]:
    """Process WLAN data."""

    wlan = {}

    for interface in wlan_list:
        index = list(Wlan).index(interface)
        info = {}
        for pair in MAP_WLAN:
            key, method = safe_unpack_key(pair)
            info[key.format(index)[4:]] = (
                method(data.get(key.format(index)))
                if method
                else data.get(key.format(index))
            )
        wlan[interface.value] = info

    return wlan
