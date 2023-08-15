"""Process module

This module has methods to process different types of data received from the device
"""

from datetime import datetime
from typing import Any

from asusrouter import (
    AsusRouterIdentityError,
    ConnectedDevice,
    FilterDevice,
    PortForwarding,
)
from asusrouter.const import (
    AIMESH,
    CLIENTS,
    CLIENTS_HISTORIC,
    CONNECTION_TYPE,
    CPU_USAGE,
    DELIMITER_PARENTAL_CONTROL_ITEM,
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
    MAP_IDENTITY,
    MAP_NVRAM,
    MAP_OVPN_STATUS,
    MAP_PARENTAL_CONTROL_ITEM,
    MAP_PARENTAL_CONTROL_TYPE,
    MEMORY_USAGE,
    NAME,
    NETDEV,
    NODE,
    ONLINE,
    PARENTAL_CONTROL,
    PORT_FORWARDING,
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
    TOTAL,
    TYPE,
    UNKNOWN,
    USB,
    USED,
    VPN,
    VPN_CLIENT,
    WAN,
    WANLINK_STATE,
    WLAN,
    WLAN_TYPE,
    PORT,
    INFO,
    PORT_TYPES,
    PORT_STATUS,
    DEVICES,
    CONVERTERS,
    MAP_CONNECTED_DEVICE,
)
from asusrouter.util import calculators, converters, parsers


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


def data_cpu(raw: dict[str, Any], prev_cpu: dict[str, Any] | None) -> dict[str, Any]:
    """Process CPU data"""

    cpu = {}
    cpu_usage = raw.get(CPU_USAGE)
    if cpu_usage:
        cpu = parsers.cpu_usage(raw=cpu_usage)

        # Calculate actual usage in percents and save it. Only if there was old data for CPU
        if prev_cpu:
            for item in cpu:
                if item in prev_cpu:
                    cpu[item] = calculators.usage_in_dict(
                        after=cpu[item],
                        before=prev_cpu[item],
                    )
    # Keep last data
    elif prev_cpu:
        cpu = prev_cpu

    return cpu


def data_firmware(raw, fw_current) -> dict[str, Any]:
    """Process firmware data"""

    # Firmware
    firmware = raw
    fw_new = parsers.firmware_string(raw.get("webs_state_info", "")) or fw_current

    firmware[STATE] = fw_current < fw_new
    firmware["current"] = str(fw_current)
    firmware["available"] = str(fw_new)

    return firmware


def data_network(
    raw: dict[str, Any],
    prev_network: dict[str, Any],
    time_delta: int | None,
    dualwan: bool,
) -> dict[str, Any]:
    """Process network data"""

    network = {}
    # Data in Bytes for traffic and bits/s for speeds
    netdev = raw.get(NETDEV)
    if netdev:
        # Calculate RX and TX from the HEX values.
        # If there is no current value, but there was one before, get it from storage.
        # Traffic resets only on device reboot or when above the limit.
        # Device disconnect / reconnect does NOT reset it
        network = parsers.network_usage(raw=netdev)
        if prev_network:
            # Calculate speeds
            network = parsers.network_speed(
                after=network,
                before=prev_network,
                time_delta=time_delta,
            )
    # Keep last data
    elif prev_network:
        network = prev_network

    if USB not in network and dualwan:
        network[USB] = {}

    return network


def data_port_status(
    raw: dict[str, Any], prev_ports: dict[str, Any], mac: str
) -> dict[str, Any]:
    """Process port status data"""

    ports = {
        LAN: {},
        USB: {},
        WAN: {},
    }
    port_info = raw.get(f"{PORT}_{INFO}")
    if port_info:
        data = port_info[mac]
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
    # Keep last data
    elif prev_ports:
        port = prev_ports

    return ports


def data_ram(raw: dict[str, Any], prev_ram: dict[str, Any]) -> dict[str, Any]:
    """Process RAM data"""

    ram = {}
    # Data is in KiB. To get MB as they are shown in the device Web-GUI,
    # should be devided by 1024 (yes, those will be MiB)
    memory_usage = raw.get(MEMORY_USAGE)
    if memory_usage:
        # Populate RAM with known values
        ram = parsers.ram_usage(raw=memory_usage)

        # Calculate usage in percents
        if USED in ram and TOTAL in ram:
            ram = calculators.usage_in_dict(after=ram)
    # Keep last data
    elif prev_ram:
        ram = prev_ram

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


def data_wan(raw: dict[str, Any], prev_wan: dict[str, Any]) -> dict[str, Any]:
    """Process WAN data"""

    wan = {}
    wanlink_state = raw.get(WANLINK_STATE)
    if wanlink_state:
        # Populate WAN with known values
        wan = parsers.wan_state(raw=wanlink_state)
    # Keep last data
    elif prev_wan:
        wan = prev_wan

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
        for device in raw["get_cfg_clientlist"][0]
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
