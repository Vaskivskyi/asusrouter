"""AsusRouter module"""

from __future__ import annotations

import aiohttp
import asyncio
from datetime import datetime
import logging
from typing import Any, Callable

from asusrouter import (
    AsusDevice,
    AsusRouter404,
    AsusRouterError,
    AsusRouterIdentityError,
    AsusRouterServerDisconnectedError,
    AsusRouterServiceError,
    AsusRouterValueError,
    Connection,
    FilterDevice,
    Monitor,
)
from asusrouter.const import (
    AIMESH,
    AR_DEVICE_IDENTITY,
    AR_HOOK_DEVICES,
    AR_KEY_AURARGB,
    AR_KEY_DEVICES,
    AR_KEY_LED,
    AR_KEY_LEDG_COUNT,
    AR_KEY_LEDG_RGB,
    AR_KEY_LEDG_SCHEME,
    AR_KEY_LEDG_SCHEME_OLD,
    AR_KEY_PARENTAL_CONTROL,
    AR_KEY_SERVICE_COMMAND,
    AR_KEY_SERVICE_MODIFY,
    AR_KEY_SERVICE_REPLY,
    AR_LEDG_MODE,
    AR_MAP_PARENTAL_CONTROL,
    AR_PATH,
    AR_SERVICE_COMMAND,
    AR_SERVICE_CONTROL,
    AR_SERVICE_DROP_CONNECTION,
    BOOTTIME,
    CLIENTS,
    CONNECTION_TYPE,
    CONVERTERS,
    CPU,
    CPU_USAGE,
    DEFAULT_ACTION_MODE,
    DEFAULT_CACHE_TIME,
    DEFAULT_SLEEP_TIME,
    DEVICEMAP,
    ENDHOOKS,
    ENDPOINT,
    ENDPOINTS,
    ERRNO,
    ERROR_IDENTITY,
    ERROR_SERVICE,
    ERROR_SERVICE_UNKNOWN,
    ERROR_VALUE,
    ETHERNET_PORTS,
    FIRMWARE,
    GUEST,
    HD_DATA,
    INFO,
    IP,
    ISO,
    KEY_ACTION_MODE,
    KEY_HOOK,
    KEY_NETWORK,
    KEY_WAN,
    LAN,
    LINK_RATE,
    MAC,
    MAIN,
    MAP_CONNECTED_DEVICE,
    MAP_OVPN_STATUS,
    MEMORY_USAGE,
    NETDEV,
    NETWORK,
    ONLINE,
    RAM,
    TOTAL,
    UPDATE_CLIENTS,
    USED,
    WANLINK_STATE,
    Merge,
    MSG_ERROR,
    MSG_INFO,
    MSG_SUCCESS,
    NODE,
    NVRAM_TEMPLATE,
    ONBOARDING,
    PARAM_COLOR,
    PARAM_COUNT,
    PARAM_MODE,
    PORT,
    PORT_STATUS,
    PORT_TYPES,
    PORTS,
    RANGE_OVPN_CLIENTS,
    RSSI,
    SPEED_TYPES,
    STATE,
    STATUS,
    SYS,
    SYSINFO,
    TEMPERATURE,
    TIMESTAMP,
    TRACK_SERVICES_LED,
    UNKNOWN,
    USB,
    VPN,
    VPN_CLIENT,
    WAN,
)
from asusrouter.dataclass import AiMeshDevice, ConnectedDevice
from asusrouter.util import calculators, compilers, converters, parsers

_LOGGER = logging.getLogger(__name__)


class AsusRouter:
    """The interface class"""

    def __init__(
        self,
        host: str,
        username: str | None = None,
        password: str | None = None,
        port: int | None = None,
        use_ssl: bool = False,
        cert_check: bool = True,
        cert_path: str = "",
        cache_time: int = DEFAULT_CACHE_TIME,
        enable_monitor: bool = True,
        enable_control: bool = False,
        session: aiohttp.ClientSession | None = None,
    ):
        """Init"""

        self._host: str = host

        self._cache_time: int = cache_time
        self._enable_monitor: bool = enable_monitor
        self._enable_control: bool = enable_control

        self._device_cpu_cores: list[int] | None = None
        self._device_ports: dict[str, str] | None = None
        self._device_boottime: datetime | None = None

        # Monitors
        self.monitor: dict[str, Monitor] = {
            endpoint: Monitor() for endpoint in ENDPOINT
        }
        self.monitor_arg = dict()
        for key, value in ENDHOOKS.items():
            self.monitor[key] = Monitor()
            self.monitor_arg[key] = f"hook={compilers.hook(value)}"
        self._init_monitor_methods()

        self._identity: AsusDevice | None = None
        self._ledg_color: dict[int, dict[str, int]] | None = None
        self._ledg_count: int = 0
        self._ledg_mode: int | None = None
        self._status_led: bool = False

        self._flag_reboot: bool = False

        """Connect"""
        self.connection = Connection(
            host=self._host,
            username=username,
            password=password,
            port=port,
            use_ssl=use_ssl,
            cert_check=cert_check,
            cert_path=cert_path,
            session=session,
        )

    def _init_monitor_methods(self) -> None:
        """Initialize monitors"""

        self.monitor_method = {
            DEVICEMAP: self._process_monitor_devicemap,
            ETHERNET_PORTS: self._process_monitor_ethernet_ports,
            FIRMWARE: self._process_monitor_firmware,
            MAIN: self._process_monitor_main,
            ONBOARDING: self._process_monitor_onboarding,
            PORT_STATUS: self._process_monitor_port_status,
            SYSINFO: self._process_monitor_sysinfo,
            TEMPERATURE: self._process_monitor_temperature,
            UPDATE_CLIENTS: self._process_monitor_update_clients,
            VPN: self._process_monitor_vpn,
        }

    def _mark_reboot(self) -> None:
        """Mark reboot"""

        self._flag_reboot = True

    async def _check_flags(self) -> None:
        """Check flags"""

        if self._flag_reboot:
            await self.async_handle_reboot()

    ### MAIN CONTROL -->

    async def async_check_endpoint(self, endpoint: str) -> bool:
        """Check if endpoint exists"""

        try:
            result = await self.connection.async_load(endpoint)
            return True
        except AsusRouter404:
            return False

    async def async_connect(self) -> bool:
        """Connect to the device"""

        try:
            await self.connection.async_connect()
        except Exception as ex:
            raise ex

        await self.async_identify()

        return True

    async def async_disconnect(self) -> bool:
        """Disconnect from the device"""

        try:
            await self.connection.async_disconnect()
        except Exception as ex:
            raise ex

        return True

    async def async_drop_connection(self) -> bool:
        """Drop connection when device will not reply because of our actions"""

        try:
            await self.connection.async_drop_connection()
        except Exception as ex:
            raise ex

        return True

    async def async_get_identity(self, force: bool = False) -> AsusDevice:
        """Return device identity"""

        if not self._identity or force:
            await self.async_identify()

        return self._identity

    async def async_identify(self) -> None:
        """Identify the device"""

        _LOGGER.debug(MSG_INFO["identifying"])

        # Compile
        query = list()
        for item in AR_DEVICE_IDENTITY:
            query.append(item)

        # Collect data
        message = compilers.nvram(query)
        try:
            raw = await self.async_hook(message, force=True)
        except Exception as ex:
            raise AsusRouterIdentityError(ERROR_IDENTITY.format(self._host, str(ex)))

        # Parse
        identity = dict()
        for item in AR_DEVICE_IDENTITY:
            key = item.get()
            try:
                data = item.method(raw[item.value]) if item.method else raw[item.value]
                if key in identity:
                    if type(identity[key]) is list:
                        identity[key].extend(data)
                    else:
                        identity[key] = data
                else:
                    identity[key] = data
            except Exception as ex:
                raise AsusRouterIdentityError(
                    ERROR_IDENTITY.format(self._host, str(ex))
                )

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

        identity[ENDPOINTS] = dict()

        # Check by page
        for endpoint in ENDPOINT:
            self.monitor[endpoint].enabled = identity[ENDPOINTS][
                endpoint
            ] = await self.async_check_endpoint(ENDPOINT[endpoint])
        identity["update_networkmapd"] = await self.async_check_endpoint(
            endpoint=AR_PATH["networkmap"]
        )

        # Check RGBG / AURA
        try:
            data = await self.connection.async_load(AR_PATH["rgb"])
            if AR_KEY_AURARGB in data:
                identity["aura"] = True
            elif AR_KEY_LEDG_COUNT in data:
                identity["ledg"] = True
                self._ledg_count = parsers.ledg_count(data)
        except AsusRouter404 as ex:
            """Do nothing"""

        # Save static values
        self._status_led = raw[AR_KEY_LED]

        self._identity = AsusDevice(**identity)

        _LOGGER.debug(MSG_SUCCESS["identity"])

    ### <-- MAIN CONTROL

    ### DATA PROCESSING -->

    async def async_api_load(
        self,
        endpoint: str | None = None,
        command: str = "",
    ) -> dict[str, Any]:
        """Load API endpoint"""

        # Endpoint should be selected
        if endpoint is None:
            _LOGGER.debug(MSG_INFO["empty_request"])
            return {}

        # Process endpoint
        try:
            result = await self.connection.async_run_command(
                command=command, endpoint=endpoint
            )
        except Exception as ex:
            raise ex

        return result

    async def async_command(
        self,
        commands: dict[str, str] | None = None,
        action_mode: str = DEFAULT_ACTION_MODE,
        apply_to: str = AR_PATH["command"],
    ) -> dict[str, Any]:
        """Command device to run a service or set parameter"""

        result = {}

        if not self._enable_control:
            _LOGGER.error(MSG_ERROR["disabled_control"])
            return result

        request: dict = {
            KEY_ACTION_MODE: action_mode,
        }
        if commands is not None:
            for command in commands:
                request[command] = commands[command]

        try:
            result = await self.connection.async_run_command(
                command=str(request), endpoint=apply_to
            )
        except Exception as ex:
            raise ex

        return result

    async def async_hook(
        self, hook: str | None = None, force: bool = False
    ) -> dict[str, Any]:
        """Hook data from device"""

        result = {}

        if not self._enable_monitor and not force:
            _LOGGER.error(MSG_ERROR["disabled_monitor"])
            return result

        if hook is None:
            _LOGGER.debug(MSG_INFO["empty_request"])
            return result

        try:
            result = await self.connection.async_run_command(
                command="{}={}".format(KEY_HOOK, hook)
            )
        except Exception as ex:
            raise ex

        # Check for errors during hook
        if self.connection.error:
            _LOGGER.debug(MSG_INFO["error_flag"])
            await self.async_handle_error()

        return result

    async def async_load(self, page: str | None = None) -> dict[str, Any]:
        """Return the data from the page"""

        result = {}

        if not self._enable_monitor:
            _LOGGER.error(MSG_ERROR["disabled_monitor"])
            return result

        if page is None:
            _LOGGER.debug(MSG_INFO["empty_request"])
            return result

        try:
            result = await self.connection.async_run_command(command="", endpoint=page)
        except AsusRouter404 as ex:
            raise ex
        except Exception as ex:
            raise ex

        return result

    ### <-- DATA PROCESSING

    ### MONITORS -->

    async def async_monitor(self, endpoint: str) -> None:
        """Monitor an endpoint"""

        # Check flags before monitoring for new data
        await self._check_flags()

        # Check whether to run
        if not await self.async_monitor_should_run(endpoint):
            return

        process: Callable[[str], dict[str, Any]] = self.monitor_method.get(endpoint)

        try:
            # Start
            self.monitor[endpoint].start()
            monitor = Monitor()
            # Hook data
            raw = await self.async_api_load(
                compilers.endpoint(endpoint, self._identity),
                command=self.monitor_arg.get(endpoint, str()),
            )
            # Reset time
            monitor.reset()

            # Process data

            result = process(raw, time=monitor.time)
            for key, data in result.items():
                monitor[key] = data

            # Finish and save data
            monitor.finish()
            self.monitor[endpoint] = monitor

        except AsusRouterError as ex:
            self.monitor[endpoint].drop()
            raise ex

        return

    def _process_monitor_devicemap(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `devicemap` endpoint"""

        # Devicemap
        devicemap = raw

        # Boot time
        boottime = dict()
        # Calculate boot time. Since precision is 1 second, could be that old and new are 1 sec different.
        # In this case, we should not change the boot time, but keep the previous value to avoid regular changes
        if SYS in devicemap and "uptimeStr" in devicemap[SYS]:
            time = parsers.uptime(devicemap[SYS]["uptimeStr"])
            timestamp = int(time.timestamp())

            boottime[TIMESTAMP] = timestamp
            boottime[ISO] = time.isoformat()

            # If previous boot time exists
            if BOOTTIME in self.monitor[DEVICEMAP]:
                _timestamp = self.monitor[DEVICEMAP][BOOTTIME][TIMESTAMP]
                _time = datetime.fromtimestamp(_timestamp)
                # Leave the same boot time, since we don't know the new correct time
                if (
                    time == _time
                    or abs(timestamp - _timestamp) < 2
                    or timestamp - _timestamp < 0
                ):
                    boottime = self.monitor[DEVICEMAP][BOOTTIME]
                # Boot time changed -> there was reboot
                else:
                    boottime[TIMESTAMP] = timestamp
                    boottime[ISO] = time.isoformat()
                    # Mark reboot
                    self._mark_reboot()

        # VPN
        vpn = dict()
        vpnmap = devicemap.get(VPN)
        if vpnmap:
            for num in RANGE_OVPN_CLIENTS:
                key = f"{VPN_CLIENT}{num}"
                vpn[key] = dict()
                if f"{key}_{STATE}" in vpnmap:
                    status = converters.int_from_str(vpnmap[f"{key}_{STATE}"])
                    vpn[key][STATE] = True if status > 0 else False
                    vpn[key][STATUS] = MAP_OVPN_STATUS.get(
                        status, f"{UNKNOWN} ({status})"
                    )
                if f"{key}_{ERRNO}" in vpnmap:
                    vpn[key][ERRNO] = converters.int_from_str(vpnmap[f"{key}_{ERRNO}"])

        return {
            DEVICEMAP: devicemap,
            BOOTTIME: boottime,
            VPN: vpn,
        }

    def _process_monitor_ethernet_ports(
        self, raw: Any, time: datetime
    ) -> dict[str, Any]:
        """Process data from `ethernet ports` endpoint"""

        # Ports info
        ports = {
            LAN: dict(),
            WAN: dict(),
        }
        data = raw["portSpeed"]
        for port in data:
            port_type = port[0:3].lower()
            port_id = converters.int_from_str(port[3:])
            value = SPEED_TYPES.get(data[port])
            ports[port_type][port_id] = {
                STATE: converters.bool_from_any(value),
                LINK_RATE: value,
            }

        return {
            PORTS: ports,
        }

    def _process_monitor_firmware(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `firmware` endpoint"""

        # Firmware
        firmware = raw
        fw_current = self._identity.firmware
        fw_new = parsers.firmware_string(raw["webs_state_info"])

        firmware["state"] = True if fw_current < fw_new else False
        firmware["current"] = str(fw_current)
        firmware["available"] = str(fw_new)

        return {
            FIRMWARE: firmware,
        }

    def _process_monitor_main(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `main` endpoint"""

        # CPU
        cpu = dict()
        if CPU_USAGE in raw:

            cpu = parsers.cpu_usage(raw=raw[CPU_USAGE])

            # Calculate actual usage in percents and save it. Only if there was old data for CPU
            if self.monitor[MAIN].ready and CPU in self.monitor[MAIN]:
                for item in cpu:
                    if item in self.monitor[MAIN][CPU]:
                        cpu[item] = calculators.usage_in_dict(
                            after=cpu[item],
                            before=self.monitor[MAIN][CPU][item],
                        )
        # Keep last data
        elif self.monitor[MAIN].ready and CPU in self.monitor[MAIN]:
            cpu = self.monitor[MAIN][CPU]

        # RAM
        ram = dict()
        ## Data is in KiB. To get MB as they are shown in the device Web-GUI, should be devided by 1024 (yes, those will be MiB)
        if MEMORY_USAGE in raw:
            # Populate RAM with known values
            ram = parsers.ram_usage(raw=raw[MEMORY_USAGE])

            # Calculate usage in percents
            if USED in ram and TOTAL in ram:
                ram = calculators.usage_in_dict(after=ram)
        # Keep last data
        elif self.monitor[MAIN].ready and RAM in self.monitor[MAIN]:
            ram = self.monitor[MAIN][RAM]

        # Network
        network = dict()
        ## Data in Bytes for traffic and bits/s for speeds
        if NETDEV in raw:
            # Calculate RX and TX from the HEX values. If there is no current value, but there was one before, get it from storage. Traffic resets only on device reboot or when above the limit. Device disconnect / reconnect does NOT reset it
            network = parsers.network_usage(raw=raw[NETDEV])

            if self.monitor[MAIN].ready and NETWORK in self.monitor[MAIN]:
                # Calculate speeds
                time_delta = (time - self.monitor[MAIN].time).total_seconds()
                network = parsers.network_speed(
                    after=network,
                    before=self.monitor[MAIN][KEY_NETWORK],
                    time_delta=time_delta,
                )
        # Keep last data
        elif self.monitor[MAIN].ready and NETWORK in self.monitor[MAIN]:
            network = self.monitor[MAIN][NETWORK]

        if not USB in network and "dualwan" in self._identity.services:
            network[USB] = dict()

        # WAN
        wan = dict()
        if WANLINK_STATE in raw:
            # Populate WAN with known values
            wan = parsers.wan_state(raw=raw[WANLINK_STATE])
        # Keep last data
        elif self.monitor[MAIN].ready and WAN in self.monitor[MAIN]:
            wan = self.monitor[MAIN][KEY_WAN]

        return {
            CPU: cpu,
            NETWORK: network,
            RAM: ram,
            WAN: wan,
        }

    def _process_monitor_onboarding(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `onboarding` endpoint"""

        # AiMesh nodes state
        aimesh = dict()
        data = raw["get_cfg_clientlist"][0]
        for device in data:
            node = parsers.aimesh_node(device)
            aimesh[node.mac] = node

        # Client list
        clients = dict()
        data = raw["get_allclientlist"][0]
        for node in data:
            for connection in data[node]:
                for mac in data[node][connection]:
                    convert = converters.onboarding_connection(connection)
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

    def _process_monitor_port_status(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `port status` endpoint"""

        # Ports info
        ports = {
            LAN: dict(),
            USB: dict(),
            WAN: dict(),
        }
        data = raw[f"{PORT}_{INFO}"][self._identity.mac]
        for port in data:
            port_type = PORT_TYPES.get(port[0])
            port_id = converters.int_from_str(port[1:])
            # Replace needed key/value pairs
            for key in CONVERTERS[PORT_STATUS]:
                if key.value in data[port]:
                    data[port][key.get()] = key.method(data[port][key.value])
                    data[port].pop(key.value)
            ports[port_type][port_id] = data[port]

        return {
            PORTS: ports,
        }

    def _process_monitor_sysinfo(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `sysinfo` endpoint"""

        # Sysinfo
        sysinfo = raw

        return {
            SYSINFO: sysinfo,
        }

    def _process_monitor_temperature(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `temperature` endpoint"""

        # Temperature
        temperature = raw

        return {
            TEMPERATURE: temperature,
        }

    def _process_monitor_update_clients(
        self, raw: Any, time: datetime
    ) -> dict[str, Any]:
        """Process data from `update_clients` endpoint"""

        # Clients
        clients = dict()
        if "nmpClient" in raw:
            data = raw["nmpClient"][0]
            for mac, description in data.items():
                if converters.is_mac_address(mac):
                    clients[mac] = description

        if "fromNetworkmapd" in raw:
            data = raw["fromNetworkmapd"][0]
            for mac, description in data.items():
                if converters.is_mac_address(mac):
                    clients[mac] = description

        return {
            CLIENTS: clients,
        }

    def _process_monitor_vpn(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `vpn` endpoint"""

        # VPN
        vpn = raw

        return {
            VPN: vpn,
        }

    ### <-- MONITORS

    ### TECHNICAL -->

    async def async_monitor_available(self, monitor: str) -> bool:
        """Check whether monitor is available"""

        # Monitor does not exist
        if not monitor in self.monitor:
            return False

        # Monitor is disabled
        if self.monitor[monitor].enabled != True:
            return False

        return True

    async def async_monitor_cached(self, monitor: str, value: Any) -> bool:
        """Check whether monitor has cached value"""

        now = datetime.utcnow()
        if (
            not self.monitor[monitor].ready
            or not value in self.monitor[monitor]
            or self._cache_time < (now - self.monitor[monitor].time).total_seconds()
        ):
            return False

        return True

    async def async_monitor_should_run(self, monitor: str) -> bool:
        """Check whether monitor should be run"""

        # Monitor is not available
        if await self.async_monitor_available(monitor) == False:
            return False

        # Monitor is already running - wait to complete
        if self.monitor[monitor].active:
            while self.monitor[monitor].active:
                await asyncio.sleep(DEFAULT_SLEEP_TIME)
            return False

        return True

    async def _async_handle_erorr(self) -> None:
        """Actions to be taken on connection error"""

        # Drop history dependent monitor values
        for (monitor, data) in HD_DATA:
            if monitor in self.monitor and data in self.monitor[monitor]:
                self.monitor[monitor].pop(data)

        return

    ### <-- TECHNICAL

    async def async_handle_reboot(self) -> None:
        """Actions to be taken on reboot"""

        await self.async_keep_state_led()

        return

    ### PROCESS DATA -->

    @staticmethod
    def _process_data_none(raw: dict[str, Any]) -> dict[str, Any]:
        """Don't process the data"""

        return raw

    @staticmethod
    def _process_data_connected_devices(
        raw: dict[str, Any]
    ) -> dict[str, ConnectedDevice]:
        """Process data for the connected devices"""

        for mac, description in raw.items():
            for attribute, keys in MAP_CONNECTED_DEVICE.items():
                value = None

                for key in keys:
                    if description.get(key.value):
                        value = key.method(description[key.value])
                        break

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

    ### <-- PROCESS DATA

    ### RETURN DATA -->

    async def async_get_data(
        self,
        data: str,
        monitor: str | list[str],
        merge: Merge = Merge.ANY,
        process: Callable[[str], dict[str, Any]] = _process_data_none,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Return data from the first available monitor in the list"""

        result = dict()

        # Convert to list if only one monitor is set
        monitor = [monitor] if type(monitor) == str else monitor

        # Create a list of monitors
        monitors = list()

        # Check if monitors are available
        for item in monitor:
            if await self.async_monitor_available(item):
                monitors.append(item)

                # In this mode we need only one of the monitors
                if merge == Merge.ANY:
                    break

        # If monitor list is empty return empty dict
        if len(monitors) == 0:
            return {}

        # Process monitors
        for monitor in monitors:

            # Value is not cached or cache is disabled
            if not await self.async_monitor_cached(monitor, data) or use_cache == False:
                await self.async_monitor(monitor)

            # Receive data
            part = self.monitor[monitor].get(data or {})

            # Update data
            compilers.update_rec(result, part)

        # Process data
        result = process(result)

        # Return data
        return result

    async def async_get_aimesh(self, use_cache: bool = True) -> dict[str, AiMeshDevice]:
        """Return AiMesh map"""

        return await self.async_get_data(
            data=AIMESH, monitor=ONBOARDING, use_cache=use_cache
        )

    async def async_get_boottime(self, use_cache: bool = True) -> dict[str, Any]:
        """Return boottime data"""

        return await self.async_get_data(
            data=BOOTTIME, monitor=DEVICEMAP, use_cache=use_cache
        )

    async def async_get_cpu(self, use_cache: bool = True) -> dict[str, float]:
        """Return CPU data"""

        return await self.async_get_data(data=CPU, monitor=MAIN, use_cache=use_cache)

    async def async_get_connected_devices(
        self, use_cache: bool = True
    ) -> dict[str, ConnectedDevice]:
        """Return connected devices data"""

        return await self.async_get_data(
            data=CLIENTS,
            monitor=[UPDATE_CLIENTS, ONBOARDING],
            merge=Merge.ALL,
            use_cache=use_cache,
            process=self._process_data_connected_devices,
        )

    async def async_get_devicemap(self, use_cache: bool = True) -> dict[str, Any]:
        """Return devicemap data"""

        return await self.async_get_data(
            data=DEVICEMAP, monitor=DEVICEMAP, use_cache=use_cache
        )

    async def async_get_firmware(
        self, use_cache: bool = True
    ) -> dict[str, AiMeshDevice]:
        """Return firmware data"""

        return await self.async_get_data(
            data=FIRMWARE, monitor=FIRMWARE, use_cache=use_cache
        )

    async def async_get_network(
        self, use_cache: bool = True
    ) -> dict[str, (int | float)]:
        """Return network data"""

        return await self.async_get_data(
            data=NETWORK, monitor=MAIN, use_cache=use_cache
        )

    async def async_get_ports(
        self, use_cache: bool = True
    ) -> dict[str, dict[str, int]]:
        """Return ports data"""

        return await self.async_get_data(
            data=PORTS, monitor=[PORT_STATUS, ETHERNET_PORTS], use_cache=use_cache
        )

    async def async_get_ram(self, use_cache: bool = True) -> dict[str, (int | float)]:
        """Return RAM data"""

        return await self.async_get_data(data=RAM, monitor=MAIN, use_cache=use_cache)

    async def async_get_sysinfo(self, use_cache: bool = True) -> dict[str, Any]:
        """Return sysinfo data"""

        return await self.async_get_data(
            data=SYSINFO, monitor=SYSINFO, use_cache=use_cache
        )

    async def async_get_temperature(self, use_cache: bool = True) -> dict[str, Any]:
        """Raturn temperature data"""

        return await self.async_get_data(
            data=TEMPERATURE, monitor=TEMPERATURE, use_cache=use_cache
        )

    async def async_get_vpn(self, use_cache: bool = True) -> dict[str, Any]:
        """Return VPN data"""

        return await self.async_get_data(
            data=VPN, monitor=[DEVICEMAP, VPN], merge=Merge.ALL, use_cache=use_cache
        )

    async def async_get_wan(self, use_cache: bool = True) -> dict[str, str]:
        """Return WAN data"""

        return await self.async_get_data(data=WAN, monitor=MAIN, use_cache=use_cache)

    ### LEGACY -->

    async def async_get_cpu_labels(self) -> list[str]:
        """Return list of CPU cores"""

        raw = await self.async_get_cpu()
        return [item for item in raw]

    async def async_get_network_labels(self) -> list[str]:
        """Return list of network interfaces"""

        raw = await self.async_get_network()
        return [item for item in raw]

    ### NOT PROCESSED -->

    async def async_get_gwlan(self) -> dict[str, Any]:
        """Get state of guest WLAN by id"""

        ids = await self.async_get_gwlan_ids()

        # NVRAM values to check
        nvram = list()
        for id in ids:
            for value in NVRAM_TEMPLATE["GWLAN"]:
                nvram.append(value.value.format(id))

        try:
            data = await self.async_hook(compilers.nvram(nvram))
        except AsusRouterError as ex:
            raise ex
        for id in ids:
            for value in NVRAM_TEMPLATE["GWLAN"]:
                data[value.value.format(id)] = value.method(
                    data[value.value.format(id)]
                )

        return data

    async def async_get_gwlan_ids(self) -> list[int]:
        """Return list of guest WLAN ids"""

        ids = list()

        wlans = await self.async_get_wlan_ids()

        for wlan in wlans:
            for i in range(1, 4):
                ids.append(f"{wlan}.{i}")

        return ids

    ### PARENTAL CONTROL -->
    async def async_apply_parental_control_rules(
        self,
        rules: dict[str, FilterDevice],
    ) -> bool:
        """Apply parental control rules"""

        request = compilers.parental_control(rules)
        request["action_mode"] = "apply"

        return await self.async_service_run(
            service="restart_firewall",
            arguments=request,
        )

    async def async_get_parental_control(self) -> dict[str, Any]:
        """Return parental control status"""

        # NVRAM values to check
        nvram = list()
        nvram.append(AR_KEY_PARENTAL_CONTROL.value)
        for value in AR_MAP_PARENTAL_CONTROL:
            nvram.append(value)

        data = await self.async_hook(compilers.nvram(nvram))
        data = parsers.parental_control(data)

        return data

    async def async_get_parental_control_rules(
        self,
        macs: str | list[str] | None = None,
    ) -> dict[str, FilterDevice]:
        """Return parental control rules"""

        pc: dict = await self.async_get_parental_control()
        rules = pc.get("list", dict())

        # Return the full list if no device specified
        if macs is None:
            return rules

        # Return only devices of interest
        result = dict()
        macs = converters.as_list(macs)
        for mac in macs:
            if mac in rules:
                result[mac] = rules[mac]
        return result

    async def async_remove_parental_control_rules(
        self,
        macs: str | list[str] | None = None,
        rules: FilterDevice | list[FilterDevice] = None,
        apply: bool = True,
    ) -> dict[str, FilterDevice]:
        """Remove parental control rules"""

        macs = list() if macs is None else converters.as_list(macs)
        rules = list() if rules is None else converters.as_list(rules)

        # Get current rules
        cr: dict = await self.async_get_parental_control_rules()

        # Remove old rules for these MACs
        for mac in macs:
            if mac in cr:
                cr.pop(mac)
        for rule in rules:
            if rule.mac in cr:
                cr.pop(rule.mac)

        # Apply new rules
        if apply:
            await self.async_apply_parental_control_rules(cr)

        # Return the new rules
        return cr

    async def async_set_parental_control_rules(
        self,
        rules: FilterDevice | list[FilterDevice],
    ) -> bool:
        """Set parental control rules"""

        rules = converters.as_list(rules)

        # Remove old rules for these MACs and get the rest of the list
        cr = await self.async_remove_parental_control_rules(rules, apply=False)

        # Add new rules
        for rule in rules:
            cr[rule.mac] = rule

        # Apply new rules
        return await self.async_apply_parental_control_rules(cr)

    ### <-- PARENTAL CONTROL

    async def async_get_wlan(self) -> dict[str, Any]:
        """Get state of WLAN by id"""

        ids = await self.async_get_wlan_ids()

        # NVRAM values to check
        nvram = list()
        for id in ids:
            for value in NVRAM_TEMPLATE["WLAN"]:
                nvram.append(value.value.format(id))

        try:
            data = await self.async_hook(compilers.nvram(nvram))
        except AsusRouterError as ex:
            raise ex
        for id in ids:
            for value in NVRAM_TEMPLATE["WLAN"]:
                data[value.value.format(id)] = value.method(
                    data[value.value.format(id)]
                )

        return data

    async def async_get_wlan_ids(self) -> list[int]:
        """Return list of WLAN ids"""

        ids = list()

        interfaces = await self.async_get_network_labels()
        for value in interfaces:
            if value[:4] == "WLAN":
                ids.append(int(value[-1:]))

        return ids

    ### <-- RETURN DATA

    ### SERVICE RUN -->

    async def async_service_run(
        self,
        service: str,
        arguments: dict[str, Any] | None = None,
        expect_modify: bool = True,
        drop_connection: bool = False,
    ) -> bool:
        """Generic service to run"""

        commands = {
            AR_KEY_SERVICE_COMMAND: service,
        }

        if arguments:
            commands.update(arguments)

        try:
            result = await self.async_command(commands=commands)
        except AsusRouterServerDisconnectedError as ex:
            # For services, that will block any further connections
            if drop_connection:
                _LOGGER.debug(MSG_INFO["drop_connection_service"].format(service))
                await self.async_drop_connection()
                return True
            else:
                raise ex

        if (
            not AR_KEY_SERVICE_REPLY in result
            or result[AR_KEY_SERVICE_REPLY] != service
            or not AR_KEY_SERVICE_MODIFY in result
        ):
            raise AsusRouterServiceError(ERROR_SERVICE.format(service, result))

        _LOGGER.debug(MSG_INFO["service"].format(service, arguments, result))

        services = service.split(";")
        if any(service in TRACK_SERVICES_LED for service in services):
            await self.async_keep_state_led()

        if expect_modify:
            return converters.bool_from_any(result[AR_KEY_SERVICE_MODIFY])
        return True

    ### SERVICES -->

    async def async_service_control(self, target: str, mode: str) -> bool:
        """Start / stop / (force) restart service"""

        if not target in AR_SERVICE_CONTROL or not mode in AR_SERVICE_CONTROL[target]:
            raise AsusRouterServiceError(ERROR_SERVICE_UNKNOWN.format(target, mode))

        service = AR_SERVICE_COMMAND[mode].format(target)

        drop_connection = False
        if target in AR_SERVICE_DROP_CONNECTION:
            drop_connection = True

        return await self.async_service_run(
            service=service, drop_connection=drop_connection
        )

    async def async_service_led_get(self) -> bool | None:
        """Return status of the LEDs"""

        key = AR_KEY_LED
        raw = await self.async_hook(compilers.nvram(key))
        if not converters.none_or_str(raw[key]):
            return None
        value = converters.bool_from_any(raw[key])
        self._status_led = value
        return value

    async def async_service_led_set(self, value: bool | int | str) -> bool:
        """Set status of the LEDs"""

        value_to_set = converters.bool_from_any(value)

        service = "start_ctrl_led"
        arguments = {
            AR_KEY_LED: converters.int_from_bool(value_to_set),
        }
        result = await self.async_service_run(service=service, arguments=arguments)
        if result:
            self._status_led = value_to_set
        return result

    async def async_service_ledg_get(self) -> dict[str, Any] | None:
        """Return status of RGB LEDs in LEDG scheme"""

        nvram = list()
        for mode in AR_LEDG_MODE:
            nvram.append(AR_KEY_LEDG_RGB.format(mode))
        nvram.append(AR_KEY_LEDG_SCHEME)
        nvram.append(AR_KEY_LEDG_SCHEME_OLD)

        data = await self.async_hook(compilers.nvram(nvram))

        ledg = dict()
        if AR_KEY_LEDG_SCHEME in data and data[AR_KEY_LEDG_SCHEME] != str():
            self._ledg_mode = data[AR_KEY_LEDG_SCHEME]
            ledg[AR_KEY_LEDG_SCHEME] = self._ledg_mode
        else:
            return None

        if AR_KEY_LEDG_RGB.format(self._ledg_mode) in data:
            self._ledg_color = parsers.rgb(
                data[AR_KEY_LEDG_RGB.format(self._ledg_mode)]
            )

        return {
            PARAM_COLOR: self._ledg_color,
            PARAM_COUNT: self._ledg_count,
            PARAM_MODE: self._ledg_mode,
        }

    async def async_service_ledg_set(
        self, mode: int, color: dict[int, dict[str, int]]
    ) -> bool:
        """Set state of RGB LEDs in LEDG scheme"""

        # If none LEDs
        if self._ledg_count == 0:
            return False

        if not mode in AR_LEDG_MODE:
            raise (AsusRouterValueError(ERROR_VALUE.format(mode)))

        # Check for the known state
        if not self._ledg_mode or not self._ledg_color:
            await self.async_service_ledg_get()

        colors = calculators.rgb(color)
        for num in range(1, self._ledg_count + 1):
            if not num in colors:
                if self._ledg_color and num in self._ledg_color:
                    colors[num] = self._ledg_color[num]
                else:
                    colors[num] = dict()

        color_to_set = compilers.rgb(colors)

        result = await self.async_load(
            f"{AR_PATH['ledg']}?{AR_KEY_LEDG_SCHEME}={mode}&ledg_rgb={color_to_set}"
        )

        if "statusCode" in result and int(result["statusCode"]) == 200:
            return True

        return False

    ### <-- SERVICES

    async def async_keep_state_led(self) -> bool:
        """Keep state of LEDs"""

        # Only for Merlin firmware, so sysinfo should be present
        if self._identity.sysinfo and self.led == False:
            await self.async_service_led_set(True)
            await self.async_service_led_set(False)

    @property
    def connected(self) -> bool:
        return self.connection.connected

    @property
    def led(self) -> bool:
        return self._status_led

    @property
    def ledg_count(self) -> int:
        return self._ledg_count
