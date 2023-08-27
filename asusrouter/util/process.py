"""Process module

This module has methods to process different types of data received from the device
"""

from datetime import datetime
from typing import Any

from asusrouter import (
    AsusRouterIdentityError,
    AsusRouterValueError,
    ConnectedDevice,
    FilterDevice,
    PortForwarding,
)
from asusrouter.const import (
    AIMESH,
    CLIENTS,
    CLIENTS_HISTORIC,
    CONNECTION_TYPE,
    CONVERTERS,
    DELIMITER_PARENTAL_CONTROL_ITEM,
    DEVICES,
    ERRNO,
    ERROR_IDENTITY,
    GUEST,
    GWLAN,
    IP,
    ISO,
    KEY_PARENTAL_CONTROL_MAC,
    KEY_PARENTAL_CONTROL_STATE,
    KEY_PARENTAL_CONTROL_TYPE,
    KEY_PORT_FORWARDING_LIST,
    KEY_PORT_FORWARDING_STATE,
    LAN,
    LED,
    LED_VAL,
    LINK_RATE,
    MAC,
    MAP_CONNECTED_DEVICE,
    MAP_IDENTITY,
    MAP_NETWORK,
    MAP_NVRAM,
    MAP_OVPN_STATUS,
    MAP_PARENTAL_CONTROL_ITEM,
    MAP_PARENTAL_CONTROL_TYPE,
    MAP_WAN,
    NAME,
    NODE,
    ONLINE,
    PARENTAL_CONTROL,
    PORT_FORWARDING,
    PORT_STATUS,
    PORT_TYPES,
    PORTS,
    RANGE_GWLAN,
    RANGE_OVPN_CLIENTS,
    RSSI,
    RULES,
    SPEED_TYPES,
    STATE,
    STATUS,
    SYS,
    SYSINFO,
    TEMPERATURE,
    TIMEMAP,
    TIMESTAMP,
    TYPE,
    UNKNOWN,
    USB,
    VPN,
    VPN_CLIENT,
    WAN,
    WLAN,
    WLAN_TYPE,
)
from asusrouter.util import converters, parsers


def data_boottime(
    devicemap: dict[str, Any], prev_boottime: dict[str, Any] | None
) -> dict[str, Any]:
    """Process boottime data"""

    # Reboot flag
    reboot = False

    boottime = {}

    # Since precision is 1 second, could be that old and new are 1 sec different.
    # In this case, we should not change the boot time,
    # but keep the previous value to avoid regular changes
    sys = devicemap.get(SYS)
    if sys:
        uptime_str = sys.get("uptimeStr")
        if uptime_str:
            time = parsers.uptime(uptime_str)
            timestamp = int(time.timestamp())

            boottime[TIMESTAMP] = timestamp
            boottime[ISO] = time.isoformat()

            if prev_boottime:
                _timestamp = prev_boottime[TIMESTAMP]

                # Check for reboot
                time_diff = timestamp - _timestamp
                if abs(time_diff) >= 2 and time_diff >= 0:
                    reboot = True
                else:
                    boottime = prev_boottime

    return boottime, reboot


def data_connected_devices(raw: dict[str, Any]) -> dict[str, ConnectedDevice]:
    """Process connected devices data"""

    for mac, description in raw.items():
        for attribute, keys in MAP_CONNECTED_DEVICE.items():
            value = next(
                (
                    key.method(description[key.value])
                    for key in keys
                    if description.get(key.value)
                ),
                None,
            )

            if value:
                raw[mac][attribute] = value

        # Remove unknown attributes
        description = {
            attribute: value
            for attribute, value in description.items()
            if attribute in MAP_CONNECTED_DEVICE
        }

        raw[mac] = ConnectedDevice(**description)

    return raw


def data_cpu(cpu_usage: dict[str, Any], prev_cpu: dict[str, Any]) -> dict[str, Any]:
    """Process CPU data"""

    cpu = data_cpu_usage(cpu_usage)

    # Safe calculate of actual usage if previous data is available
    if prev_cpu:
        for item, after in cpu.items():
            if item in prev_cpu:
                before = prev_cpu[item]
                after["usage"] = safe_usage_historic(
                    after["used"], after["total"], before["used"], before["total"]
                )

    return cpu


def data_cpu_usage(raw: dict[str, Any]) -> dict[str, Any]:
    """CPU usage parser"""

    # Populate total
    cpu = {"total": {"total": 0.0, "used": 0.0}}

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


def data_firmware(raw_firmware, fw_current) -> dict[str, Any]:
    """Process firmware data"""

    # Firmware
    firmware = raw_firmware
    fw_new = (
        parsers.firmware_string(raw_firmware.get("webs_state_info", "")) or fw_current
    )

    firmware[STATE] = fw_current < fw_new
    firmware["current"] = str(fw_current)
    firmware["available"] = str(fw_new)

    return firmware


def data_network(
    netdev: dict[str, Any],
    prev_network: dict[str, Any],
    time_delta: int | None,
) -> dict[str, Any]:
    """Process network data.

    The data is in Bytes for traffic and bits/s for speeds"""

    # Calculate RX and TX from the HEX values.
    network = data_network_usage(netdev)

    # Calculate speeds if previous data is available
    if prev_network:
        network = data_network_speed(network, prev_network, time_delta)

    return network


def data_network_speed(
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


def data_network_usage(raw: dict[str, Any]) -> dict[str, Any]:
    """Process network usage data"""

    network = {}
    for interface in MAP_NETWORK:
        data = {}
        for traffic_type in ("rx", "tx"):
            try:
                # Convert string with HEX value to int
                value = converters.int_from_str(
                    raw.get(f"{interface.value}_{traffic_type}"), base=16
                )
                # Check that value is integer
                if isinstance(value, int):
                    data[traffic_type] = value
            except AsusRouterValueError:
                continue
        if len(data) > 0:
            network[interface.get()] = data

    return network


def data_port_status(port_info: dict[str, Any], mac: str) -> dict[str, Any]:
    """Process port status data"""

    ports = {
        LAN: {},
        USB: {},
        WAN: {},
    }

    data = port_info.get(mac)
    if data:
        for port in data:
            port_type = PORT_TYPES.get(port[0])
            port_id = converters.int_from_str(port[1:])
            # Replace needed key/value pairs
            for key in CONVERTERS[PORT_STATUS]:
                if key.value in data[port]:
                    data[port][key.get()] = key.method(data[port][key.value])
                    if key.get() != key.value:
                        data[port].pop(key.value)
            # Temporary solution for USB
            if port_type == USB and DEVICES in data[port]:
                data[port][STATE] = True
            ports[port_type][port_id] = data[port]

    return ports


def data_ram(memory_usage: dict[str, Any]) -> dict[str, Any]:
    """Process RAM data"""

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


def data_vpn(devicemap: dict[str, Any]) -> dict[str, Any]:
    """Process VPN data"""

    vpn = {}
    vpnmap = devicemap.get(VPN)
    if vpnmap:
        for num in RANGE_OVPN_CLIENTS:
            key = f"{VPN_CLIENT}{num}"
            vpn[key] = {}
            state_key = f"{key}_{STATE}"
            if state_key in vpnmap:
                status = converters.int_from_str(vpnmap[state_key])
                vpn[key][STATE] = status > 0
                vpn[key][STATUS] = MAP_OVPN_STATUS.get(status, f"{UNKNOWN} ({status})")
            errno_key = f"{key}_{ERRNO}"
            if errno_key in vpnmap:
                vpn[key][ERRNO] = converters.int_from_str(vpnmap[errno_key])

    return vpn


def data_wan(wanlink_state: dict[str, Any]) -> dict[str, Any]:
    """Process WAN data"""

    wan = {}

    for key in MAP_WAN:
        key_value = key.value
        state_value = wanlink_state.get(key_value)
        if state_value:
            wan[key.get()] = key.method(state_value) if key.method else state_value

    return wan


def data_wlan(
    raw: dict[str, Any], available_wlan: list[str]
) -> (dict[str, Any], dict[str, Any]):
    """Process WLAN and GWLAN data received from NVRAM"""

    wlan = {}
    gwlan = {}

    wlan_map = MAP_NVRAM[WLAN]
    gwlan_map = MAP_NVRAM[GWLAN]

    # WLAN
    wlan = {
        wlan_type: {
            (key.value.format(wlan_id))[4:]: key.method(
                raw.get(key.value.format(wlan_id), None)
            )
            for key in wlan_map
        }
        for wlan_type, wlan_id in (
            (wlan_type, WLAN_TYPE.get(wlan_type)) for wlan_type in available_wlan
        )
        # Careful here - an explicit check is required
        # because `if wlan_id` will return false for `wlan_id = 0`
        if wlan_id is not None
    }

    # GWLAN
    gwlan = {
        f"{wlan_type}_{gwlan_id}": {
            (key.value.format(wlan_id))[4:]: key.method(
                raw.get(key.value.format(f"{wlan_id}.{gwlan_id}"), None)
            )
            for key in gwlan_map
        }
        for wlan_type, wlan_id in (
            (wlan_type, WLAN_TYPE.get(wlan_type)) for wlan_type in available_wlan
        )
        # Careful here - an explicit check is required
        # because `if wlan_id` will return false for `wlan_id = 0`
        if wlan_id is not None
        for gwlan_id in RANGE_GWLAN
    }

    return wlan, gwlan


def device_identity(raw: dict[str, Any], host: str) -> dict[str, Any]:
    """Parse identity-related data from the router's API"""

    identity = {}
    for item in MAP_IDENTITY:
        key = item.get()
        try:
            data = item.method(raw[item.value]) if item.method else raw[item.value]
            if key in identity:
                if isinstance(identity[key], list):
                    identity[key].extend(data)
                else:
                    identity[key] = data
            else:
                identity[key] = data
        except Exception as ex:
            raise AsusRouterIdentityError(ERROR_IDENTITY.format(host, str(ex))) from ex

    # Mac (for some Merlin devices missing label_mac)
    if identity["mac"] is None or identity["mac"] == str():
        if identity["lan_mac"] is not None:
            identity["mac"] = identity["lan_mac"]
        elif identity["wan_mac"] is not None:
            identity["mac"] = identity["wan_mac"]

    identity.pop("lan_mac")
    identity.pop("wan_mac")

    # Firmware
    identity["firmware"] = parsers.firmware_string(
        f"{identity['fw_major']}.{identity['fw_minor']}.{identity['fw_build']}"
    )
    identity.pop("fw_major")
    identity.pop("fw_minor")
    identity.pop("fw_build")

    return identity


def monitor_devices(raw: Any, time: datetime) -> dict[str, Any]:
    """Process data from `devices` endpoint"""

    # Clients
    clients = {}
    if "get_clientlist" in raw:
        data = raw["get_clientlist"]
        clients = {
            mac: description
            for mac, description in data.items()
            if converters.is_mac_address(mac)
        }

    return {
        CLIENTS: clients,
    }


def monitor_ethernet_ports(raw: Any, time: datetime) -> dict[str, Any]:
    """Process data from `ethernet ports` endpoint"""

    # Ports info
    ports = {
        LAN: {},
        WAN: {},
    }
    if "portSpeed" in raw:
        data = raw["portSpeed"]
        for port, value in data.items():
            port_type = port[0:3].lower()
            port_id = converters.int_from_str(port[3:])
            link_rate = SPEED_TYPES.get(value)
            ports[port_type][port_id] = {
                STATE: converters.bool_from_any(link_rate),
                LINK_RATE: link_rate,
            }

    return {
        PORTS: ports,
    }


def monitor_light(raw: Any, time: datetime) -> dict[str, Any]:
    """Process data from `light` endpoint"""

    # LED
    led = {}
    led_val = raw.get(LED_VAL)
    if led_val is not None:
        led_state = converters.bool_from_any(led_val)
        led[STATE] = led_state
        # self._state_led = led_state

    return {
        LED: led,
    }


def monitor_onboarding(raw: Any, time: datetime) -> dict[str, Any]:
    """Process data from `onboarding` endpoint"""

    # AiMesh nodes state
    aimesh = {
        node.mac: node
        for device in raw.get("get_cfg_clientlist", [[]])[0]
        for node in [parsers.aimesh_node(device)]
    }

    # Client list
    clients = {}
    data = raw["get_allclientlist"][0]
    for node in data:
        for connection in data[node]:
            convert = converters.onboarding_connection(connection)
            for mac in data[node][connection]:
                description = {
                    CONNECTION_TYPE: convert[CONNECTION_TYPE],
                    GUEST: convert[GUEST],
                    IP: converters.none_or_str(
                        data[node][connection][mac].get(IP, None)
                    ),
                    MAC: mac,
                    NODE: node,
                    ONLINE: True,
                    RSSI: data[node][connection][mac].get(RSSI, None),
                }
                clients[mac] = description

    return {
        AIMESH: aimesh,
        CLIENTS: clients,
    }


def monitor_parental_control(raw: Any, time: datetime) -> dict[str, Any]:
    """Process data from `parental control` endpoint"""

    parental_control = {}

    # State
    parental_control[STATE] = None
    if KEY_PARENTAL_CONTROL_STATE in raw:
        parental_control[STATE] = converters.bool_from_any(
            raw[KEY_PARENTAL_CONTROL_STATE]
        )

    # Rules
    rules = {}

    if raw.get(KEY_PARENTAL_CONTROL_MAC) != raw.get(KEY_PARENTAL_CONTROL_TYPE):
        as_is = {
            element.get(): [
                element.method(temp_element)
                for temp_element in raw[element.value].split(
                    DELIMITER_PARENTAL_CONTROL_ITEM
                )
            ]
            for element in MAP_PARENTAL_CONTROL_ITEM
        }

        number = len(as_is[MAC])
        for i in range(number):
            rules[as_is[MAC][i]] = FilterDevice(
                mac=as_is[MAC][i],
                name=as_is[NAME][i],
                type=MAP_PARENTAL_CONTROL_TYPE.get(as_is[TYPE][i], UNKNOWN),
                timemap=as_is[TIMEMAP][i] if i < len(as_is[TIMEMAP]) else None,
            )

    parental_control[RULES] = rules.copy()

    return {PARENTAL_CONTROL: parental_control}


def monitor_port_forwarding(raw: Any, time: datetime) -> dict[str, Any]:
    """Process data from `port forwarding` endpoint"""

    port_forwarding = {}

    # State
    port_forwarding[STATE] = None
    if KEY_PORT_FORWARDING_STATE in raw:
        port_forwarding[STATE] = converters.bool_from_any(
            raw[KEY_PORT_FORWARDING_STATE]
        )

    # Rules
    if KEY_PORT_FORWARDING_LIST in raw:
        rules = []
        data = raw[KEY_PORT_FORWARDING_LIST]
        rule_list = data.split("&#60")
        for rule in rule_list:
            if rule == str():
                continue
            part = rule.split("&#62")
            rules.append(
                PortForwarding(
                    name=converters.none_or_any(part[0]),
                    ip=part[2],
                    port=converters.none_or_any(part[3]),
                    protocol=part[4],
                    ip_external=converters.none_or_any(part[5]),
                    port_external=part[1],
                )
            )
        port_forwarding[RULES] = rules.copy()

    return {
        PORT_FORWARDING: port_forwarding,
    }


def monitor_sysinfo(raw: Any, time: datetime) -> dict[str, Any]:
    """Process data from `sysinfo` endpoint"""

    # Sysinfo
    sysinfo = raw

    return {
        SYSINFO: sysinfo,
    }


def monitor_temperature(raw: Any, time: datetime) -> dict[str, Any]:
    """Process data from `temperature` endpoint"""

    # Temperature
    temperature = raw

    return {
        TEMPERATURE: temperature,
    }


def monitor_update_clients(raw: Any, time: datetime) -> dict[str, Any]:
    """Process data from `update_clients` endpoint"""

    # Clients
    clients_historic = {
        mac: description
        for mac, description in raw.get("nmpClient", [{}])[0].items()
        if converters.is_mac_address(mac)
    }

    clients = {
        mac: description
        for mac, description in raw.get("fromNetworkmapd", [{}])[0].items()
        if converters.is_mac_address(mac)
    }

    return {
        CLIENTS: clients,
        CLIENTS_HISTORIC: clients_historic,
    }


def monitor_vpn(raw: Any, time: datetime) -> dict[str, Any]:
    """Process data from `vpn` endpoint"""

    # VPN
    vpn = raw

    return {
        VPN: vpn,
    }


def safe_speed(
    current: (int | float),
    previous: (int | float),
    time_delta: (int | float) | None = None,
) -> float:
    """Calculate speed

    Allows calculation only of positive speed, otherwise returns 0.0"""

    if time_delta is None or time_delta == 0.0:
        return 0.0

    diff = current - previous if current > previous else 0.0

    return diff / time_delta


def safe_usage(used: int | float, total: int | float) -> float:
    """Calculate usage in percents

    Allows calculation only of positive usage, otherwise returns 0.0"""

    if total == 0:
        return 0.0

    usage = round(used / total * 100, 2)

    # Don't allow negative usage
    if usage < 0:
        return 0.0

    return usage


def safe_usage_historic(
    used: int | float,
    total: int | float,
    prev_used: int | float,
    prev_total: int | float,
) -> float:
    """Calculate usage in percents for difference between current and previous values

    This method is just an interface to calculate usage using `usage` method"""

    return safe_usage(used - prev_used, total - prev_total)
