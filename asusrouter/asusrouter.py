"""AsusRouter module"""

import logging
import asyncio
from datetime import datetime

from asusrouter import Connection, helpers

_LOGGER = logging.getLogger(__name__)

DEFAULT_SLEEP_TIME = 0.1

_MSG_SUCCESS_COMMAND = "Command was sent successfully"
_MSG_SUCCESS_HOOK = "Hook was sent successfully"
_MSG_SUCCESS_LOAD = "Page was loaded successfully"

_MSG_ERROR_NO_CONTROL = "Device is connected in no-control mode. Sending commands is blocked"
_MSG_ERROR_NO_MONITOR = "Device is connected in no-control mode. Sending hooks is blocked"

INTERFACE_TYPE = {
    "wan_ifnames": "wan",
    "wl_ifnames": "wlan",
    "wl0_vifnames": "gwlan2",
    "wl1_vifnames": "gwlan5",
    "lan_ifnames": "lan"
}

NVRAM_LIST = {
    "DEVICE": [
        "productid",
        "serial_no",
        "label_mac",
        "model",
        "pci/1/1/ATE_Brand",
    ],
    "MODE": [
        "sw_mode",
        "wlc_psta",
        "wlc_express",
    ],
    "FIRMWARE": [
        "firmver",
        "buildno",
        "extendno",
    ],
    "FUNCTIONS": [
        "rc_support",
        "ss_support",
    ],
    "INTERFACES": [
        "wans_dualwan",
        "wan_ifnames",
        "wl_ifnames",
        "wl0_vifnames",
        "wl1_vifnames",
        "lan_ifnames",
        "br0_ifnames",
    ],
    "REBOOT": [
        "reboot_schedule",
        "reboot_schedule_enable",
        "reboot_time",
    ],
    "WAN0": [
        "link_wan",
        "wan0_auxstate_t",
        "wan0_dns",
        "wan0_enable",
        "wan0_expires",
        "wan0_gateway",
        "wan0_gw_ifname",
        "wan0_gw_mac",
        "wan0_hwaddr",
        "wan0_ipaddr",
        "wan0_is_usb_modem_ready",
        "wan0_primary",
        "wan0_proto",
        "wan0_realip_ip",
        "wan0_realip_state",
        "wan0_sbstate_t",
        "wan0_state_t",
        "wan0_upnp_enable",
    ],
    "WAN1": [
        "link_wan1",
        "wan1_auxstate_t",
        "wan1_dns",
        "wan1_enable",
        "wan1_gateway",
        "wan1_gw_ifname",
        "wan1_gw_mac",
        "wan1_hwaddr",
        "wan1_ipaddr",
        "wan1_is_usb_modem_ready",
        "wan1_primary",
        "wan1_proto",
        "wan1_realip_ip",
        "wan1_realip_state",
        "wan1_sbstate_t",
        "wan1_state_t",
        "wan1_upnp_enable",
    ],
    "LAN": [
        "lan_gateway",
        "lan_hwaddr",
        "lan_ifname",
        "lan_ifnames",
        "lan_ipaddr",
        "lan_netmask",
        "lan_proto",
        "lanports",
    ],
    "WLAN0": [
        "wl0_radio",
        "wl0_ssid",
        "wl0_chanspec",
        "wl0_closed",
        "wl0_nmode_x",
        "wl0_bw",
        "wl0_auth_mode_x",
        "wl0_crypto",
        "wl0_wpa_psk",
        "wl0_mfp",
        "wl0_mbo_enable",
        "wl0_country_code",
        "wl0_maclist_x",
        "wl0_macmode",
    ],
    "WLAN1": [
        "wl1_radio",
        "wl1_ssid",
        "wl1_chanspec",
        "wl1_closed",
        "wl1_nmode_x",
        "wl1_bw",
        "wl1_auth_mode_x",
        "wl1_crypto",
        "wl1_wpa_psk",
        "wl1_mfp",
        "wl1_mbo_enable",
        "wl1_country_code",
        "wl1_maclist_x",
        "wl1_macmode",
    ],
    "GWLAN01": [
        "wl0.1_bss_enabled",
        "wl0.1_ssid",
        "wl0.1_auth_mode_x",
        "wl0.1_crypto",
        "wl0.1_key",
        "wl0.1_wpa_psk",
        "wl0.1_lanaccess",
        "wl0.1_expire",
        "wl0.1_expire_tmp",
        "wl0.1_macmode",
        "wl0.1_mbss",
        "wl0.1_sync_mode",
    ],
    "GWLAN02": [
        "wl0.2_bss_enabled",
        "wl0.2_ssid",
        "wl0.2_auth_mode_x",
        "wl0.2_crypto",
        "wl0.2_key",
        "wl0.2_wpa_psk",
        "wl0.2_lanaccess",
        "wl0.2_expire",
        "wl0.2_expire_tmp",
        "wl0.2_macmode",
        "wl0.2_mbss",
        "wl0.2_sync_mode",
    ],
    "GWLAN03": [
        "wl0.3_bss_enabled",
        "wl0.3_ssid",
        "wl0.3_auth_mode_x",
        "wl0.3_crypto",
        "wl0.3_key",
        "wl0.3_wpa_psk",
        "wl0.3_lanaccess",
        "wl0.3_expire",
        "wl0.3_expire_tmp",
        "wl0.3_macmode",
        "wl0.3_mbss",
        "wl0.3_sync_mode",
    ],
    "GWLAN11": [
        "wl1.1_bss_enabled",
        "wl1.1_ssid",
        "wl1.1_auth_mode_x",
        "wl1.1_crypto",
        "wl1.1_key",
        "wl1.1_wpa_psk",
        "wl1.1_lanaccess",
        "wl1.1_expire",
        "wl1.1_expire_tmp",
        "wl1.1_macmode",
        "wl1.1_mbss",
        "wl1.1_sync_mode",
    ],
    "GWLAN12": [
        "wl1.2_bss_enabled",
        "wl1.2_ssid",
        "wl1.2_auth_mode_x",
        "wl1.2_crypto",
        "wl1.2_key",
        "wl1.2_wpa_psk",
        "wl1.2_lanaccess",
        "wl1.2_expire",
        "wl1.2_expire_tmp",
        "wl1.2_macmode",
        "wl1.2_mbss",
        "wl1.2_sync_mode",
    ],
    "GWLAN13": [
        "wl1.3_bss_enabled",
        "wl1.3_ssid",
        "wl1.3_auth_mode_x",
        "wl1.3_crypto",
        "wl1.3_key",
        "wl1.3_wpa_psk",
        "wl1.3_lanaccess",
        "wl1.3_expire",
        "wl1.3_expire_tmp",
        "wl1.3_macmode",
        "wl1.3_mbss",
        "wl1.3_sync_mode",
    ],
}

MONITOR_MAIN = {
    "cpu_usage" : "appobj",
    "memory_usage" : "appobj",
    "netdev" : "appobj"
}

TRAFFIC_GROUPS = {
    "INTERNET" : "WAN0",    # main WAN
    "INTERNET1" : "WAN1",   # secondary WAN (USB modem / phone)
    "WIRED" : "WIRED",      # wired connections
    "BRIDGE" : "BRIDGE",    # bridge
    "WIRELESS0" : "WLAN0",  # 2.4 GHz WiFi
    "WIRELESS1" : "WLAN1",  # 5 GHz WiFi
    "WIRELESS2" : "WLAN2",  # 5 GHz WiFi #2 (<-- check)
}

NETWORK_DATA = [
    "rx",
    "tx",
]

PORT_TYPE = [
    "LAN",
    "WAN",
]

KEY_NVRAM_GET = "nvram_get"

class AsusRouter:
    """The interface class"""

    def __init__(
        self,
        host : str,
        username : str | None = None,
        password : str | None = None,
        port : int | None = None,
        use_ssl : bool = False,
        cert_check : bool = True,
        cert_path : str = "",
        cache_time : int = 5,
        enable_monitor : bool = True,
        enable_control : bool = False):
        """Init"""

        self._enable_monitor : bool = enable_monitor
        self._enable_control : bool = enable_control

        self._cache_time : int = cache_time


        self._device_cpu_cores : list | None = None
        self._device_ports : dict | None = None
        self._device_boottime: datetime | None = None


        self._monitor_main : dict | None = None
        self._monitor_main_time : datetime | None = None
        self._monitor_main_running : bool = False
        self._monitor_nvram : dict | None = None
        self._monitor_nvram_time : datetime | None = None
        self._monitor_nvram_running : bool = False
        self._monitor_misc : dict | None = None
        self._monitor_misc_time : datetime | None = None
        self._monitor_misc_running : bool = False
        self._monitor_devices : dict | None = None
        self._monitor_devices_time : datetime | None = None
        self._monitor_devices_running : bool = False


        """Connect"""
        self.connection = Connection(host = host, username = username, password = password, port = port, use_ssl = use_ssl, cert_check = cert_check, cert_path = cert_path)


    async def async_compile_hook(self, commands : dict[str, str] | None = None) -> str:
        """"Compile all the components of the hook message into one string"""

        data = ""
        if commands is not None:
            for item in commands:
                data += "{}({});".format(item, commands[item])

        return data


    async def async_compile_nvram(self, values : list[str] | str | None = None) -> str:
        """Compile all the values to ask from nvram"""

        if values is None:
            return ""

        if type(values) == str:
            return "{}({});".format(KEY_NVRAM_GET, values)

        request = ""
        for value in values:
            request += "{}({});".format(KEY_NVRAM_GET, value)
        return request


    async def async_hook(self, hook : str) -> dict:
        """Hook data from device"""

        result = {}

        if not self._enable_monitor:
            _LOGGER.error(_MSG_ERROR_NO_MONITOR)
            return result

        if hook is None:
            return result

        try:
            result = await self.connection.async_run_command("hook={}".format(hook))
            _LOGGER.debug("{}: {}".format(_MSG_SUCCESS_HOOK, hook))
        except Exception as ex:
            _LOGGER.error(ex)

        return result


    async def async_command(self, commands : dict[str, str], action_mode : str = "apply") -> dict:
        """Command device to run a service or set parameter"""

        result = {}

        if not self._enable_control:
            _LOGGER.error(_MSG_ERROR_NO_CONTROL)
            return result

        request : dict = {
            "action_mode": action_mode,
        }
        for command in commands:
            request[command] = commands[command]

        try:
            result = await self.connection.async_run_command(str(request), "applyapp.cgi")
            _LOGGER.debug("{}: {}".format(_MSG_SUCCESS_COMMAND, request))
        except Exception as ex:
            _LOGGER.error(ex)

        return result


    async def async_load(self, page : str | None = None) -> dict:
        """Return the data from the page"""

        result = {}

        if not self._enable_monitor:
            _LOGGER.error(_MSG_ERROR_NO_MONITOR)
            return result

        if page is None:
            return result

        try:
            result = await self.connection.async_run_command(command = "", endpoint = page)
            _LOGGER.debug(_MSG_SUCCESS_LOAD)
        except Exception as ex:
            _LOGGER.error(ex)

        return result

    
    async def async_monitor_main(self) -> None:
        """Get all the main monitor values. Non-cacheable"""

        while self._monitor_main_running:
            await asyncio.sleep(DEFAULT_SLEEP_TIME)
            return

        self._monitor_main_running = True

        monitor_main = dict()

        hook = await self.async_compile_hook(MONITOR_MAIN)
        data = await self.async_hook(hook)

        now = datetime.utcnow()

        ### CPU ###
        ## Not yet known what exactly is type of data. But this is the correct way to calculate usage from it

        # Check which cores CPU has or find it out and save for later
        if self._device_cpu_cores is None:
            cpu_cores = []
            for i in range(1,8):
                if "cpu{}_total".format(i) in data["cpu_usage"]:
                    cpu_cores.append(i)
                else:
                    break
            self._device_cpu_cores = cpu_cores

        # Create CPU dict in monitor_main and populate its total for the whole CPU data
        monitor_main["CPU"] = dict()
        monitor_main["CPU"]["total"] = dict()
        monitor_main["CPU"]["total"]["total"] = 0
        monitor_main["CPU"]["total"]["used"] = 0
        # Store CPU data per core. "cpu{X}_total" stays "total", "cpu{X}_usage" becomes "used". This is done to free up "usage" for the actual usage in percents
        for core in self._device_cpu_cores:
            monitor_main["CPU"][core] = dict()
            monitor_main["CPU"][core]["total"] = int(data["cpu_usage"]["cpu{}_total".format(core)])
            monitor_main["CPU"][core]["used"] = int(data["cpu_usage"]["cpu{}_usage".format(core)])
            monitor_main["CPU"]["total"]["total"] += monitor_main["CPU"][core]["total"]
            monitor_main["CPU"]["total"]["used"] += monitor_main["CPU"][core]["used"]
        # Calculate actual usage in percents and save it. Only if there was old data for CPU
        if self._monitor_main is not None:
            for item in monitor_main["CPU"]:
                monitor_main["CPU"][item]["usage"] = round(100 * (monitor_main["CPU"][item]["used"] - self._monitor_main["CPU"][item]["used"]) / (monitor_main["CPU"][item]["total"] - self._monitor_main["CPU"][item]["total"]), 2)


        ### RAM ###
        ## Data is in KiB. To get MB as they are shown in the device Web-GUI, should be devided by 1024 (yes, those will be MiB)

        # Populate RAM with known values
        monitor_main["RAM"] = dict()
        monitor_main["RAM"]["total"] = int(data["memory_usage"]["mem_total"])
        monitor_main["RAM"]["free"] = int(data["memory_usage"]["mem_free"])
        monitor_main["RAM"]["used"] = int(data["memory_usage"]["mem_used"])

        # Calculate usage in percents
        monitor_main["RAM"]["usage"] = round(100 * monitor_main["RAM"]["used"] / monitor_main["RAM"]["total"], 2)


        ### NETWORK ###
        ## Data in Bytes for traffic and bits/s for speeds

        # Calculate RX and TX from the HEX values. If there is no current value, but there was one before, get it from storage. Traffic resets only on device reboot or when above the limit. Device disconnect / reconnect does NOT reset it
        monitor_main["NETWORK"] = dict()
        for el in TRAFFIC_GROUPS:
            for nd in NETWORK_DATA:
                if "{}_{}".format(el, nd) in data["netdev"]:
                    if not TRAFFIC_GROUPS[el] in monitor_main["NETWORK"]:
                        monitor_main["NETWORK"][TRAFFIC_GROUPS[el]] = dict()
                    monitor_main["NETWORK"][TRAFFIC_GROUPS[el]][nd] = int(data["netdev"]["{}_{}".format(el, nd)], base = 16)
                elif (self._monitor_main is not None
                    and el in self._monitor_main["NETWORK"]
                    and self._monitor_main["NETWORK"][TRAFFIC_GROUPS[el]][nd] is not None
                ):
                    monitor_main["NETWORK"][TRAFFIC_GROUPS[el]][nd] = self._monitor_main["NETWORK"][TRAFFIC_GROUPS[el]][nd]

        # Calculate speeds
        if (self._monitor_main is not None
            and self._monitor_main["NETWORK"] is not None
        ):
            for el in monitor_main["NETWORK"]:
                for nd in NETWORK_DATA:
                    if el in self._monitor_main["NETWORK"]:
                        traffic_diff = monitor_main["NETWORK"][el][nd] - self._monitor_main["NETWORK"][el][nd]
                        # Handle overflow in the traffic stats, so there will not be a negative speed once per 0xFFFFFFFF + 1 bytes of data
                        if (traffic_diff < 0):
                            traffic_diff += 4294967296
                        monitor_main["NETWORK"][el]["{}_speed".format(nd)] = traffic_diff * 8 / (now - self._monitor_main_time).total_seconds()
                    else:
                        monitor_main["NETWORK"][el]["{}_speed".format(nd)] = 0

        self._monitor_main = monitor_main

        self._monitor_main_time = now
        self._monitor_main_running = False

        return


    async def async_monitor_nvram(self, groups : list[str] | str | None = None) -> None:
        """Get the NVRAM values for the specified group list"""

        while self._monitor_nvram_running:
            await asyncio.sleep(DEFAULT_SLEEP_TIME)
            return

        self._monitor_nvram_running = True

        monitor_nvram = {}

        # If none groups were sent, will return all the known NVRAM values
        if groups is None:
            groups = [*NVRAM_LIST]

        # If only one group is sent
        if type(groups) is not list:
            groups = [groups.upper()]

        requests = []
        for group in groups:
            group = group.upper()
            if group in NVRAM_LIST:
                for value in NVRAM_LIST[group]:
                    requests.append(value)
            else:
                _LOGGER.warning("There is no {} in known NVRAM groups".format(group))

        message = await self.async_compile_nvram(requests)
        result = await self.async_hook(message)

        now = datetime.utcnow()

        for item in result:
            monitor_nvram[item] = result[item]

        if self._monitor_nvram is None:
            self._monitor_nvram = dict()

        for group in monitor_nvram:
            for element in monitor_nvram:
                self._monitor_nvram[element] = monitor_nvram[element]

        self._monitor_nvram_time = now
        self._monitor_nvram_running = False

        return


    async def async_monitor_misc(self) -> None:
        """Get all other useful values"""

        while self._monitor_misc_running:
            await asyncio.sleep(DEFAULT_SLEEP_TIME)
            return

        self._monitor_misc_running = True

        if self._monitor_misc is None:
            self._monitor_misc = dict()

        monitor_misc = {}

        ### PORTS

        # Receive ports number and status (disconnected, 100 Mb/s, 1 Gb/s)
        data = await self.async_load("ajax_ethernet_ports.asp")

        now = datetime.utcnow()

        if "portSpeed" in data:
            monitor_misc["PORTS"] = dict()
            for type in PORT_TYPE:
                monitor_misc["PORTS"][type] = dict()
            for value in data["portSpeed"]:
                for type in PORT_TYPE:
                    if type in value:
                        number = value.replace(type, "")
                        monitor_misc["PORTS"][type][number] = await helpers.async_transform_port_speed(data["portSpeed"][value])
                        break

        # Load devicemap
        data = await self.async_load("ajax_status.xml")
        monitor_misc["DEVICEMAP"] = data

        # Calculate boot time. Since precision is 1 second, could be that old and new are 1 sec different. In this case, we should not change the boot time, but keep the previous value to avoid regular changes
        if "SYS" in monitor_misc["DEVICEMAP"]:
            if "uptimeStr" in monitor_misc["DEVICEMAP"]["SYS"]:
                time = await helpers.async_parse_uptime(monitor_misc["DEVICEMAP"]["SYS"]["uptimeStr"])
                timestamp = int(time.timestamp())
                if not "BOOTTIME" in monitor_misc:
                    monitor_misc["BOOTTIME"] = dict()

                if "BOOTTIME" in self._monitor_misc:
                    _timestamp = self._monitor_misc["BOOTTIME"]["timestamp"]
                    _time = datetime.fromtimestamp(_timestamp)
                    if time == _time:
                        monitor_misc["BOOTTIME"] = self._monitor_misc["BOOTTIME"]
                    elif abs(timestamp - _timestamp) < 2:
                        monitor_misc["BOOTTIME"] = self._monitor_misc["BOOTTIME"]
                    else:
                        monitor_misc["BOOTTIME"]["timestamp"] = timestamp
                        monitor_misc["BOOTTIME"]["ISO"] = time.isoformat()
                else:
                    monitor_misc["BOOTTIME"]["timestamp"] = timestamp
                    monitor_misc["BOOTTIME"]["ISO"] = time.isoformat()

                self._device_boottime = time

        self._monitor_misc = monitor_misc

        self._monitor_misc_time = now
        self._monitor_misc_running = False

        return


    async def async_monitor_devices(self) -> None:
        """Monitor connected devices"""

        while self._monitor_devices_running:
            await asyncio.sleep(DEFAULT_SLEEP_TIME)
            return

        self._monitor_devices_running = True

        if self._monitor_devices is None:
            self._monitor_devices = dict()

        monitor_devices = {}

        data = (await self.async_hook("get_clientlist()"))["get_clientlist"]

        now = datetime.utcnow()

        if "maclist" in data:
            for mac in data["maclist"]:
                monitor_devices[mac] = dict()

                # Name the device properly. If user has selected nickName manualy - it is the expected value. Else - name device set by itself or MAC address
                if (data[mac]["nickName"] is not None
                    and data[mac]["nickName"] != ""):
                    monitor_devices[mac]["name"] = data[mac]["nickName"]
                elif (data[mac]["name"] is not None
                    and data[mac]["name"] != ""):
                    monitor_devices[mac]["name"] = data[mac]["name"]
                else:
                    monitor_devices[mac]["name"] = mac

                # Let's still include MAC address
                monitor_devices[mac]["MAC"] = mac

                # IP address
                monitor_devices[mac]["IP"] = data[mac]["ip"]
                # IP type
                monitor_devices[mac]["IPMethod"] = data[mac]["ipMethod"]

                # Internet info map
                monitor_devices[mac]["internet"] = dict()
                # Connected
                if data[mac]["internetState"] is not None:
                    monitor_devices[mac]["internet"]["online"] = data[mac]["internetState"]
                # Mode
                if data[mac]["internetMode"] is not None:
                    monitor_devices[mac]["internet"]["mode"] = data[mac]["internetMode"]

                # Connection info map
                monitor_devices[mac]["connection"] = dict()

                # Type of the connection
                if data[mac]["isWL"] is not None:
                    value = int(data[mac]["isWL"])
                    if value == 1:
                        monitor_devices[mac]["connection"]["type"] = "WLAN0"
                    elif value == 2:
                        monitor_devices[mac]["connection"]["type"] = "WLAN1"
                    else:
                        monitor_devices[mac]["connection"]["type"] = "LAN"
                # Connected
                if data[mac]["isOnline"] is not None:
                    monitor_devices[mac]["connection"]["online"] = data[mac]["isOnline"]
                    
                # Only for wireless
                if monitor_devices[mac]["connection"]["type"] != "LAN":
                    # RSSI
                    if data[mac]["rssi"] is not None:
                        monitor_devices[mac]["connection"]["RSSI"] = data[mac]["rssi"]
                    # Connection time
                    if data[mac]["wlConnectTime"] is not None:
                        monitor_devices[mac]["connection"]["uptime"] = data[mac]["wlConnectTime"]
                    # Connection speeds
                    monitor_devices[mac]["connection"]["speed"] = dict()
                    raw = data[mac]["curRx"].strip()
                    value = float(raw) if raw != "" else 0.0
                    monitor_devices[mac]["connection"]["speed"]["Rx"] = value
                    raw = data[mac]["curTx"].strip()
                    value = float(raw) if raw != "" else 0.0
                    monitor_devices[mac]["connection"]["speed"]["Tx"] = value
                
                # Other info
                if (data[mac]["vendor"] is not None
                    and data[mac]["vendor"] != ""):
                    monitor_devices[mac]["vendor"] = data[mac]["vendor"]

        self._monitor_devices = monitor_devices

        self._monitor_devices_time = now
        self._monitor_devices_running = False

        return


    async def async_find_interfaces(self, use_cache : bool = True) -> None:
        """Find available interfaces/type dictionary"""
        
        if self._monitor_nvram is None:
            await self.async_monitor_nvram()
        elif use_cache == False:
            await self.async_monitor_nvram()

        ports = {}

        data = self._monitor_nvram
        
        for if_type in INTERFACE_TYPE:
            if if_type in data:
                values = data[if_type].split(" ")
                for item in values:
                    ports[item] = INTERFACE_TYPE[if_type]

        self._device_ports = ports


    async def async_initialize(self):
        """Get all the data needed at the startup"""

        await self.async_monitor_main()
        await self.async_monitor_nvram()
        await self.async_find_interfaces()
        await self.async_monitor_misc()
        await self.async_monitor_devices()


#### RETURN DATA

    async def async_get_devices(self, use_cache : bool = True) -> dict:
        """Return device list"""
        
        now = datetime.utcnow()
        if (self._monitor_devices is None
            or self._monitor_devices_time is None
            or use_cache == False
            or (use_cache == True and self._monitor_devices_time and self._cache_time < (now - self._monitor_devices_time).total_seconds())
        ):
            await self.async_monitor_devices()

        return self._monitor_devices


    async def async_get_cpu(self, use_cache : bool = True) -> dict:
        """Return CPU usage"""
        
        now = datetime.utcnow()
        if (self._monitor_main is None
            or self._monitor_main_time is None
            or use_cache == False
            or (use_cache == True and self._monitor_main_time and self._cache_time < (now - self._monitor_main_time).total_seconds())
            or self._device_cpu_cores is None
        ):
            await self.async_monitor_main()

        result = {}
        for core in self._device_cpu_cores:
            if "usage" in self._monitor_main["CPU"][core]:
                result["core_{}".format(core)] = self._monitor_main["CPU"][core]["usage"]
        if "usage" in self._monitor_main["CPU"]["total"]:
            result["total"] = self._monitor_main["CPU"]["total"]["usage"]

        return result


    async def async_get_cpu_labels(self) -> list:
        """Return list of CPU cores"""

        if self._device_cpu_cores is None:
            await self.async_monitor_main()

        result = list()
        result.append("total")
        for el in self._device_cpu_cores:
            result.append("core_{}".format(el))

        return result


    async def async_get_ram(self, use_cache : bool = True) -> dict:
        """Return RAM and its usage"""
        
        now = datetime.utcnow()
        if (self._monitor_main is None
            or use_cache == False
            or (use_cache == True
            and self._monitor_main_time
            and self._cache_time < (now - self._monitor_main_time).total_seconds())
        ):
            await self.async_monitor_main()

        result = {}
        for value in self._monitor_main["RAM"]:
            result[value] = self._monitor_main["RAM"][value]
        return result


    async def async_get_ram_labels(self) -> list:
        """Return list of CPU cores"""

        if self._device_cpu_cores is None:
            await self.async_monitor_main()

        result = list()
        for value in self._monitor_main["RAM"]:
            result.append(value)

        return result


    async def async_get_network(self, use_cache : bool = True) -> dict:
        """Return traffic and speed for all interfaces"""
        
        now = datetime.utcnow()
        if (self._monitor_main is None
            or use_cache == False
            or (use_cache == True
            and self._monitor_main_time
            and self._cache_time < (now - self._monitor_main_time).total_seconds())
        ):
            await self.async_monitor_main()

        result = {}
        for interface in self._monitor_main["NETWORK"]:
            for value in self._monitor_main["NETWORK"][interface]:
                result["{}_{}".format(interface, value)] = self._monitor_main["NETWORK"][interface][value]

        return result

    
    async def async_get_network_labels(self) -> list:
        """Return list of network interfaces"""

        if self._monitor_main is None:
            await self.async_monitor_main()

        result = list()

        for interface in self._monitor_main["NETWORK"]:
            result.append(interface)

        return result


    @property
    def connected(self) -> bool:
        return self.connection.connected

    @property
    def boottime(self) -> datetime:
        return self._device_boottime

