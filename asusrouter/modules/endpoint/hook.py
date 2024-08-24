"""Hook endpoint module."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional, Tuple

from asusrouter.modules.aura import process_aura
from asusrouter.modules.connection import ConnectionState, ConnectionStatus
from asusrouter.modules.data import AsusData, AsusDataState
from asusrouter.modules.endpoint import data_get
from asusrouter.modules.endpoint.error import AccessError
from asusrouter.modules.led import AsusLED
from asusrouter.modules.parental_control import (
    KEY_PC_BLOCK_ALL,
    KEY_PC_STATE,
    AsusBlockAll,
    AsusParentalControl,
    read_pc_rules,
)
from asusrouter.modules.port_forwarding import (
    KEY_PORT_FORWARDING_LIST,
    KEY_PORT_FORWARDING_STATE,
    AsusPortForwarding,
    PortForwardingRule,
)
from asusrouter.modules.vpnc import AsusVPNC, AsusVPNType
from asusrouter.modules.wlan import MAP_GWLAN, MAP_WLAN, Wlan
from asusrouter.tools.converters import (
    run_method,
    safe_bool,
    safe_datetime,
    safe_int,
    safe_return,
    safe_speed,
    safe_unpack_key,
    safe_unpack_keys,
    safe_usage,
    safe_usage_historic,
)
from asusrouter.tools.readers import merge_dicts
from asusrouter.tools.readers import read_json_content as read  # noqa: F401

from .hook_const import (
    MAP_NETWORK,
    MAP_OVPN_SERVER_388,
    MAP_SPEEDTEST,
    MAP_VPNC_WIREGUARD,
    MAP_WAN,
    MAP_WAN_ITEM,
    MAP_WAN_ITEM_X,
    MAP_WIREGUARD_CLIENT,
    MAP_WIREGUARD_SERVER,
)

REQUIRE_HISTORY = True
REQUIRE_WLAN = True

_LOGGER = logging.getLogger(__name__)


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process hook data."""

    # For this endpoint, the received data always depends on the sent request.
    # So, we need to check which data is available and process it accordingly.
    # Otherwise, we can accidentally overwrite the data with empty values.

    state: dict[AsusData, Any] = {}

    # Get the passed awrguments
    history: dict[AsusData, AsusDataState] = data_get(data, "history") or {}
    wlan = data_get(data, "wlan") or []

    # Aura
    if "ledg_scheme" in data:
        state[AsusData.AURA] = process_aura(data)

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

    # OpenVPN Server
    if "vpn_serverx_clientlist" in data:
        state[AsusData.OPENVPN_SERVER] = process_openvpn_server(data)

    # Parental control
    if KEY_PC_STATE in data:
        state[AsusData.PARENTAL_CONTROL] = process_parental_control(data)

    # Port forwarding
    if KEY_PORT_FORWARDING_STATE in data:
        state[AsusData.PORT_FORWARDING] = process_port_forwarding(data)

    # RAM
    if "memory_usage" in data:
        memory_usage = data.get("memory_usage", {})
        state[AsusData.RAM] = process_ram(memory_usage) if memory_usage else {}

    # Speedtest
    if "ookla_state" in data:
        speedtest = process_speedtest(data)
        state[AsusData.SPEEDTEST_RESULT] = speedtest.get("result")
        state[AsusData.SPEEDTEST] = speedtest.get("data")

    # VPNC
    if "vpnc_clientlist" in data:
        vpnc, vpnc_clientlist = process_vpnc(data)
        state[AsusData.OPENVPN_CLIENT] = vpnc[AsusVPNType.OPENVPN]
        state[AsusData.VPNC] = vpnc
        state[AsusData.VPNC_CLIENTLIST] = vpnc_clientlist
        state[AsusData.WIREGUARD_CLIENT] = vpnc[AsusVPNType.WIREGUARD]

    # WAN
    if "get_wan_unit" in data:
        state[AsusData.WAN] = process_wan(data)

    # WireGuard
    if "get_wgsc_status" in data:
        state[AsusData.WIREGUARD_SERVER] = process_wireguard_server(data)

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
                    after["used"],
                    after["total"],
                    before["used"],
                    before["total"],
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


def process_gwlan(
    data: dict[str, Any], wlan_list: list[Wlan]
) -> dict[str, Any]:
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
        time_delta = (
            datetime.now(timezone.utc) - history.timestamp
        ).total_seconds()
        network = process_network_speed(network, history.data, time_delta)

    return network


def process_network_speed(
    network: dict[str, dict[str, float]],
    prev_network: dict[str, dict[str, float]],
    time_delta: float | None,
) -> dict[str, dict[str, float]]:
    """Calculate network speed for a set period of time."""

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
    """Process network usage data."""

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


def process_openvpn_server(data: dict[str, Any]) -> dict[int, Any]:
    """Process OpenVPN server data."""

    server = {}

    # Server data
    for keys in MAP_OVPN_SERVER_388:
        key, key_to_use, method = safe_unpack_keys(keys)
        state_value = data.get(key)
        if state_value:
            server[key_to_use] = run_method(state_value, method)

    # Clients
    clients = server.get("clients", "")
    clients = clients.replace("&#62", ">").replace("&#60", "<")
    clients = clients[1:-1].split("><")
    server["clients"] = clients

    return {1: server}


def process_parental_control(data: dict[str, Any]) -> dict[str, Any]:
    """Process parental control data."""

    parental_control: dict[str, Any] = {}

    # State
    parental_control["state"] = AsusParentalControl(
        safe_int(data.get(KEY_PC_STATE), default=-999)
    )

    # Block all
    parental_control["block_all"] = AsusBlockAll(
        safe_int(data.get(KEY_PC_BLOCK_ALL), default=-999)
    )

    # Rules
    parental_control["rules"] = read_pc_rules(data)

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
        "free": safe_int(memory_usage.get("mem_free")),
        "total": safe_int(memory_usage.get("mem_total")),
        "used": safe_int(memory_usage.get("mem_used")),
    }
    # Calculate usage in percents
    if "used" in ram and "total" in ram:
        ram["usage"] = safe_usage(ram["used"], ram["total"])

    return ram


def process_speedtest(data: dict[str, Any]) -> dict[str, Any]:
    """Process Speedtest data."""

    speedtest: dict[str, Any] = {}

    # Convert the data
    for keys in MAP_SPEEDTEST:
        key, key_to_use, method = safe_unpack_keys(keys)
        state_value = data.get(key)
        if state_value:
            speedtest[key_to_use] = run_method(state_value, method)

    # Get detailed result
    test_result = speedtest.pop("result", None)

    # Get the last speedtest step
    last_run_step: Optional[dict[str, Any]] = process_speedtest_last_step(
        test_result
    )

    # Save the last tested data directly in the speedtest dict
    for key, value in last_run_step.items():
        speedtest[key] = value

    # Convert the timestamp to UTC
    speedtest["timestamp"] = safe_datetime(speedtest.get("timestamp"))

    # Rename servers list
    if "download" in speedtest:
        speedtest["download"]["server_list"] = speedtest["download"].pop(
            "servers", None
        )

    # convert bandwidth from Bps to bps
    for speed in ("download", "upload"):
        if speed in speedtest:
            speedtest[speed]["bandwidth"] = 8 * speedtest[speed].get(
                "bandwidth", 0
            )

    # Remove extra values
    speedtest.pop("type", None)

    return {
        "data": speedtest,
        "result": test_result,
    }


def process_speedtest_last_step(
    data: Optional[list[dict[str, Any]]],
) -> dict[str, Any]:
    """Process Speedtest progress data."""

    last_step: dict[str, Any] = {}

    # Check the length of the data
    if not data or len(data) < 2:
        return last_step

    # Check the last step
    last_step = data[-2]

    # If the last step is a result, then the test is finished
    # and we already have all the data
    if last_step.get("type") != "result":
        return {}

    return last_step


def process_vpnc(
    data: dict[str, Any],
) -> Tuple[dict[AsusVPNType, dict[int, Any]], str]:
    """Process VPNC data."""

    vpnc = {}

    # Get client list
    vpnc_clientlist = (
        data.get("vpnc_clientlist", "")
        .replace("&#62", ">")
        .replace("&#60", "<")
    )
    if vpnc_clientlist != "":
        clients = vpnc_clientlist.split("<")
        vpnc_unit = 0
        for client in clients:
            if client == str():
                continue
            part = client.split(">")
            # Format: name, type, id, login, password, active, vpnc_id, ?, ?, ?, ?, `Web`
            if len(part) < 7:
                continue
            vpnc_id = safe_int(part[6])
            vpnc[vpnc_id] = {
                "type": (
                    AsusVPNType(part[1])
                    if part[1] in [e.value for e in AsusVPNType]
                    else AsusVPNType.UNKNOWN
                ),
                "id": safe_int(part[2]),
                "name": safe_return(part[0]),
                "login": safe_return(part[3]),
                "password": safe_return(part[4]),
                "active": safe_bool(part[5]),
                "vpnc_unit": vpnc_unit,
            }
            vpnc_unit += 1

    # Get clients status
    get_vpnc_status = data.get("get_vpnc_status")
    if get_vpnc_status:
        clients = get_vpnc_status.split("<")
        for client in clients:
            if client == str():
                continue
            part = client.split(">")
            vpnc_id = safe_int(part[2])
            state_code = safe_int(part[0])
            error_code = safe_int(part[1])
            vpnc[vpnc_id].update(
                {
                    "state": (
                        AsusVPNC(state_code)
                        if state_code in [e.value for e in AsusVPNC]
                        else AsusVPNC.UNKNOWN
                    ),
                    "error": (
                        AccessError(error_code)
                        if error_code in [e.value for e in AccessError]
                        else AccessError.UNKNOWN
                    ),
                }
            )

    # Re-sort the data by VPN type / id
    vpn: dict[AsusVPNType, dict[int, Any]] = {
        AsusVPNType.L2TP: {},
        AsusVPNType.OPENVPN: {},
        AsusVPNType.PPTP: {},
        AsusVPNType.SURFSHARK: {},
        AsusVPNType.WIREGUARD: {},
        AsusVPNType.UNKNOWN: {},
    }

    for vpnc_id, info in vpnc.items():
        sorted_id = info.pop("id", None)
        sorted_type = info.pop("type", None)
        info["vpnc_id"] = vpnc_id
        vpn[sorted_type][sorted_id] = info

    # Process WireGuard data
    vpn[AsusVPNType.WIREGUARD] = merge_dicts(
        vpn[AsusVPNType.WIREGUARD], process_vpnc_wireguard(data)
    )
    # Fill missing clients with unknown state
    for num in range(1, 6):
        if num not in vpn[AsusVPNType.WIREGUARD]:
            vpn[AsusVPNType.WIREGUARD][num] = {
                "state": AsusVPNC.UNKNOWN,
                "error": AccessError.NO_ERROR,
            }
        if num not in vpn[AsusVPNType.OPENVPN]:
            vpn[AsusVPNType.OPENVPN][num] = {
                "state": AsusVPNC.UNKNOWN,
                "error": AccessError.NO_ERROR,
            }

    # Remove UNKNOWN VPN type if it's empty
    if not vpn[AsusVPNType.UNKNOWN]:
        vpn.pop(AsusVPNType.UNKNOWN, None)

    return vpn, vpnc_clientlist


def process_vpnc_wireguard(data: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """Process VPNC WireGuard data."""

    wireguard = {}

    for num in range(1, 6):
        client = {}
        for keys in MAP_VPNC_WIREGUARD:
            key, key_to_use, method = safe_unpack_keys(keys)
            state_value = data.get(f"wgc{num}_{key}")
            if state_value:
                client[key_to_use] = run_method(state_value, method)
        if client:
            wireguard[num] = client

    return wireguard


def process_wan(data: dict[str, Any]) -> dict[Any, dict[str, Any]]:
    """Process WAN data."""

    wan: dict[str | int, dict[str, Any]] = {}

    # General data
    wan["internet"] = {}
    for keys in MAP_WAN:
        key, key_to_use, method = safe_unpack_keys(keys)
        state_value = data.get(key)
        if state_value is not None:
            wan["internet"][key_to_use] = run_method(state_value, method)

    # Per-interface data
    for num in (0, 1):
        interface = {}
        for keys in MAP_WAN_ITEM:
            key, key_to_use, method = safe_unpack_keys(keys)
            state_value = data.get(f"wan{num}_{key}")
            if state_value is not None:
                interface[key_to_use] = run_method(state_value, method)
        for extra, extra_key in zip(("", "x"), ("main", "extra")):
            interface[extra_key] = {}
            for keys in MAP_WAN_ITEM_X:
                key, key_to_use, method = safe_unpack_keys(keys)
                state_value = data.get(f"wan{num}_{extra}{key}")
                if state_value is not None:
                    interface[extra_key][key_to_use] = run_method(
                        state_value, method
                    )
        if interface:
            wan[num] = interface

    # Re-sort needed values
    wan[0]["link"] = wan["internet"].pop("link_0", None)
    wan[1]["link"] = wan["internet"].pop("link_1", None)

    # Check state on links
    for num in (0, 1):
        if wan[num].get("link") == ConnectionState.DISCONNECTED:
            wan[num]["state"] = ConnectionStatus.DISCONNECTED

    # WAN aggregation
    aggregation_state = wan["internet"].pop("aggregation_state", None)
    if aggregation_state is not None:
        wan["aggregation"] = {
            "state": aggregation_state,
            "ports": wan["internet"].pop("aggregation_ports", None),
        }

    # Dual WAN
    dualwan_mode = wan["internet"].pop("dualwan_mode", None)
    dualwan_priority = wan["internet"].pop("dualwan_priority", None)
    if dualwan_mode is not None and dualwan_priority is not None:
        wan["dualwan"] = {
            "mode": dualwan_mode,
            "priority": dualwan_priority,
        }
        # Check whether it is actually active
        if wan["dualwan"]["priority"][1] == "none":
            wan["dualwan"]["priority"][1] = None
            wan["dualwan"]["state"] = False
        else:
            wan["dualwan"]["state"] = True

    # Assign main IP address
    wan["internet"]["ip_address"] = wan[wan["internet"]["unit"]]["main"][
        "ip_address"
    ]

    return wan


def process_wireguard_server(
    data: dict[str, Any],
) -> dict[int, dict[str, Any]]:
    """Process WireGuard data."""

    wireguard = {}

    # Server data
    for keys in MAP_WIREGUARD_SERVER:
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
                    wireguard["clients"][client.get("index")]["state"] = (
                        ConnectionState(client.get("status"))
                    )

    # Remove the `status` value
    wireguard.pop("status", None)

    return {1: wireguard}


def process_wlan(
    data: dict[str, Any], wlan_list: list[Wlan]
) -> dict[str, Any]:
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
