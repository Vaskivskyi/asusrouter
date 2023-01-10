"""AsusRouter module"""

from __future__ import annotations

import aiohttp
import asyncio
from datetime import datetime
import logging
from typing import Any, Awaitable, Callable

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
    AR_KEY_CPU,
    AR_KEY_DEVICES,
    AR_KEY_LED,
    AR_KEY_LEDG_COUNT,
    AR_KEY_LEDG_RGB,
    AR_KEY_LEDG_SCHEME,
    AR_KEY_LEDG_SCHEME_OLD,
    AR_KEY_NETWORK,
    AR_KEY_PARENTAL_CONTROL,
    AR_KEY_RAM,
    AR_KEY_SERVICE_COMMAND,
    AR_KEY_SERVICE_MODIFY,
    AR_KEY_SERVICE_REPLY,
    AR_KEY_WAN,
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
    DATA_BY_CORE,
    DATA_TOTAL,
    DATA_USAGE,
    DATA_USED,
    DEFAULT_ACTION_MODE,
    DEFAULT_CACHE_TIME,
    DEFAULT_SLEEP_TIME,
    DEVICEMAP,
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
    INFO,
    INTERFACE_TYPE,
    IP,
    ISO,
    KEY_ACTION_MODE,
    KEY_CPU,
    KEY_HOOK,
    KEY_NETWORK,
    KEY_RAM,
    KEY_VPN,
    KEY_WAN,
    LAN,
    LINK_RATE,
    MAC,
    MAP_OVPN_STATUS,
    Merge,
    MONITOR_MAIN,
    MSG_ERROR,
    MSG_INFO,
    MSG_SUCCESS,
    NODE,
    NVRAM_LIST,
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
from asusrouter.dataclass import AiMeshDevice
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

        self.monitor: dict[str, Monitor] = {
            endpoint: Monitor() for endpoint in ENDPOINT
        }
        self._init_monitor_methods()

        self._monitor_main: Monitor = Monitor()
        self._monitor_nvram: Monitor = Monitor()
        self._monitor_misc: Monitor = Monitor()
        self._monitor_devices: Monitor = Monitor()

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
        """Initialie monitors"""

        self.monitor_method = {
            DEVICEMAP: self._process_monitor_devicemap,
            ETHERNET_PORTS: self._process_monitor_ethernet_ports,
            FIRMWARE: self._process_monitor_firmware,
            ONBOARDING: self._process_monitor_onboarding,
            PORT_STATUS: self._process_monitor_port_status,
            SYSINFO: self._process_monitor_sysinfo,
            TEMPERATURE: self._process_monitor_temperature,
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

    async def async_monitor_main(self) -> None:
        """Get all the main monitor values. Non-cacheable"""

        while self._monitor_main.active:
            await asyncio.sleep(DEFAULT_SLEEP_TIME)
            return

        try:
            self._monitor_main.start()

            monitor_main = Monitor()

            hook = compilers.hook(MONITOR_MAIN)
            data = await self.async_hook(hook)

            monitor_main.reset()

            ### CPU ###
            ## Not yet known what exactly is type of data. But this is the correct way to calculate usage from it

            # Keep safe
            if AR_KEY_CPU in data:

                raw_cpu = data[AR_KEY_CPU]

                # Check which cores CPU has or find it out and save for later
                if self._device_cpu_cores is None:
                    self._device_cpu_cores = parsers.cpu_cores(raw=raw_cpu)

                # Traffic data from the device
                monitor_main[KEY_CPU] = parsers.cpu_usage(
                    raw=raw_cpu, cores=self._device_cpu_cores
                )

                # Calculate actual usage in percents and save it. Only if there was old data for CPU
                if self._monitor_main.ready and KEY_CPU in self._monitor_main:
                    for item in monitor_main[KEY_CPU]:
                        if item in self._monitor_main[KEY_CPU]:
                            monitor_main[KEY_CPU][item] = calculators.usage_in_dict(
                                after=monitor_main[KEY_CPU][item],
                                before=self._monitor_main[KEY_CPU][item],
                            )

            # Keep last data
            elif self._monitor_main.ready and KEY_CPU in self._monitor_main:
                monitor_main[KEY_CPU] = self._monitor_main[KEY_CPU]

            ### RAM ###
            ## Data is in KiB. To get MB as they are shown in the device Web-GUI, should be devided by 1024 (yes, those will be MiB)

            if AR_KEY_RAM in data:
                # Populate RAM with known values
                monitor_main[KEY_RAM] = parsers.ram_usage(raw=data[AR_KEY_RAM])

                # Calculate usage in percents
                if (
                    DATA_USED in monitor_main[KEY_RAM]
                    and DATA_TOTAL in monitor_main[KEY_RAM]
                ):
                    monitor_main[KEY_RAM] = calculators.usage_in_dict(
                        after=monitor_main[KEY_RAM]
                    )
            # Keep last data
            elif self._monitor_main.ready and KEY_RAM in self._monitor_main:
                monitor_main[KEY_RAM] = self._monitor_main[KEY_RAM]

            ### NETWORK ###
            ## Data in Bytes for traffic and bits/s for speeds

            if AR_KEY_NETWORK in data:
                # Calculate RX and TX from the HEX values. If there is no current value, but there was one before, get it from storage. Traffic resets only on device reboot or when above the limit. Device disconnect / reconnect does NOT reset it
                monitor_main[KEY_NETWORK] = parsers.network_usage(
                    raw=data[AR_KEY_NETWORK]
                )

                if self._monitor_main.ready and KEY_NETWORK in self._monitor_main:
                    # Calculate speeds
                    time_delta = (
                        monitor_main.time - self._monitor_main.time
                    ).total_seconds()
                    monitor_main[KEY_NETWORK] = parsers.network_speed(
                        after=monitor_main[KEY_NETWORK],
                        before=self._monitor_main[KEY_NETWORK],
                        time_delta=time_delta,
                    )

            # Keep last data
            elif self._monitor_main.ready and KEY_NETWORK in self._monitor_main:
                monitor_main[KEY_NETWORK] = self._monitor_main[KEY_NETWORK]

            ### WAN STATE ###

            if AR_KEY_WAN in data:
                # Populate WAN with known values
                monitor_main[KEY_WAN] = parsers.wan_state(raw=data[AR_KEY_WAN])

            # Keep last data
            elif self._monitor_main.ready and KEY_WAN in self._monitor_main:
                monitor_main[KEY_WAN] = self._monitor_main[KEY_WAN]

            monitor_main.finish()
            self._monitor_main = monitor_main
        except AsusRouterError as ex:
            self._monitor_main.drop()
            raise ex

        return

    async def async_monitor_nvram(self, groups: list[str] | str | None = None) -> None:
        """Get the NVRAM values for the specified group list"""

        while self._monitor_nvram.active:
            await asyncio.sleep(DEFAULT_SLEEP_TIME)
            return

        try:
            self._monitor_nvram.start()

            monitor_nvram = Monitor()

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
                    _LOGGER.warning(
                        "There is no {} in known NVRAM groups".format(group)
                    )

            message = compilers.nvram(requests)
            result = await self.async_hook(message)

            monitor_nvram.reset()

            for item in result:
                monitor_nvram[item] = result[item]

            monitor_nvram.finish()
            self._monitor_nvram = monitor_nvram
        except AsusRouterError as ex:
            self._monitor_nvram.drop()
            raise ex

        return

    async def async_monitor_misc(self) -> None:
        """Get all other useful values"""

        while self._monitor_misc.active:
            await asyncio.sleep(DEFAULT_SLEEP_TIME)
            return

        try:
            self._monitor_misc.start()

            monitor_misc = Monitor()

            # Load devicemap
            data = await self.async_load(page=ENDPOINT[DEVICEMAP])
            monitor_misc["DEVICEMAP"] = data

            ### VPN ###
            if self._identity.vpn_status:
                monitor_misc[KEY_VPN] = await self.async_load(page=AR_PATH["vpn"])
                if monitor_misc["DEVICEMAP"] and monitor_misc[KEY_VPN]:
                    monitor_misc[KEY_VPN] = compilers.vpn_from_devicemap(
                        monitor_misc[KEY_VPN], monitor_misc["DEVICEMAP"]
                    )
            else:
                monitor_misc[KEY_VPN] = compilers.vpn_from_devicemap(
                    None, monitor_misc["DEVICEMAP"]
                )

            monitor_misc.finish()
            self._monitor_misc = monitor_misc
        except AsusRouterError as ex:
            self._monitor_misc.drop()
            raise ex

        return

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
            raw = await self.async_load(compilers.endpoint(endpoint, self._identity))
            # Reset time
            monitor.reset()

            # Process data

            result = process(raw)
            for key, data in result.items():
                monitor[key] = data

            # Finish and save data
            monitor.finish()
            self.monitor[endpoint] = monitor

        except AsusRouterError as ex:
            self.monitor[endpoint].drop()
            raise ex

        return

    def _process_monitor_devicemap(self, raw: Any) -> dict[str, Any]:
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

    def _process_monitor_ethernet_ports(self, raw: Any) -> dict[str, Any]:
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

    def _process_monitor_firmware(self, raw: Any) -> dict[str, Any]:
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

    def _process_monitor_onboarding(self, raw: Any) -> dict[str, Any]:
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
                        RSSI: data[node][connection][mac].get(RSSI, None),
                    }
                    clients[mac] = description

        return {
            AIMESH: aimesh,
            CLIENTS: clients,
        }

    def _process_monitor_port_status(self, raw: Any) -> dict[str, Any]:
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

    def _process_monitor_sysinfo(self, raw: Any) -> dict[str, Any]:
        """Process data from `sysinfo` endpoint"""

        # Sysinfo
        sysinfo = raw

        return {
            SYSINFO: sysinfo,
        }

    def _process_monitor_temperature(self, raw: Any) -> dict[str, Any]:
        """Process data from `temperature` endpoint"""

        # Temperature
        temperature = raw

        return {
            TEMPERATURE: temperature,
        }

    def _process_monitor_vpn(self, raw: Any) -> dict[str, Any]:
        """Process data from `vpn` endpoint"""

        # VPN
        vpn = raw

        return {
            VPN: vpn,
        }

    async def async_monitor_devices(self) -> None:
        """Monitor connected devices"""

        while self._monitor_devices.active:
            await asyncio.sleep(DEFAULT_SLEEP_TIME)
            return

        try:
            self._monitor_devices.start()
            monitor_devices = Monitor()

            # Update device list (needed for older devices)
            await self.async_check_endpoint(AR_PATH["devices_update"])
            if self._identity.update_networkmapd:
                await self.async_check_endpoint(AR_PATH["networkmap"])
            data = await self.async_hook(AR_HOOK_DEVICES)

            monitor_devices.reset()

            onboarding = {}
            if self._identity.onboarding:
                await self.async_monitor_onboarding()
                onboarding = self.monitor[ONBOARDING][CLIENTS]

            # Search for new data
            if AR_KEY_DEVICES in data:
                data = data[AR_KEY_DEVICES]
                for mac in data:
                    if converters.is_mac_address(mac):
                        monitor_devices[mac] = compilers.connected_device(
                            parsers.connected_device(data[mac]), onboarding.get(mac)
                        )
            # Or keep last data
            elif self._monitor_devices.ready:
                monitor_devices = self._monitor_devices

            monitor_devices.finish()
            self._monitor_devices = monitor_devices
        except AsusRouterError as ex:
            self._monitor_devices.drop()
            raise ex

        return

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

    ### <-- TECHNICAL

    async def async_handle_error(self) -> None:
        """Actions to be taken on connection errors"""

        # Clear main monitor to prevent calculation errors in it
        if self._monitor_main.ready:
            self._monitor_main = Monitor()

        # Clear error
        await self.connection.async_reset_error()

        return

    async def async_handle_reboot(self) -> None:
        """Actions to be taken on reboot"""

        await self.async_keep_state_led()

        return

    async def async_find_interfaces(self, use_cache: bool = True) -> None:
        """Find available interfaces/type dictionary"""

        if not self._monitor_nvram.ready or use_cache == False:
            await self.async_monitor_nvram()

        ports = {}

        data = self._monitor_nvram

        for if_type in INTERFACE_TYPE:
            if if_type in data:
                values = data[if_type].split(" ")
                for item in values:
                    ports[item] = INTERFACE_TYPE[if_type]

        self._device_ports = ports

        return

    async def async_initialize(self):
        """Get all the data needed at the startup"""

        await self.async_monitor_main()
        await self.async_monitor_nvram()
        await self.async_find_interfaces()
        await self.async_monitor_misc()
        await self.async_monitor_devices()

    ### PROCESS DATA -->

    @staticmethod
    def _process_data_none(raw: dict[str, Any]) -> dict[str, Any]:
        """Don't process the data"""

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

            # Process data
            compilers.update_rec(result, part)

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

    async def async_get_ports(
        self, use_cache: bool = True
    ) -> dict[str, dict[str, int]]:
        """Return ports data"""

        return await self.async_get_data(
            data=PORTS, monitor=[PORT_STATUS, ETHERNET_PORTS], use_cache=use_cache
        )

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

    async def async_get_cpu(self, use_cache: bool = True) -> dict[str, float]:
        """Return CPU usage"""

        now = datetime.utcnow()
        if (
            not self._monitor_main.ready
            or not KEY_CPU in self._monitor_main
            or use_cache == False
            or (
                use_cache == True
                and self._cache_time < (now - self._monitor_main.time).total_seconds()
            )
            or self._device_cpu_cores is None
        ):
            await self.async_monitor_main()

        result = dict()

        # Check if CPU was monitored
        if not self._monitor_main.ready or not KEY_CPU in self._monitor_main:
            return result

        for core in self._device_cpu_cores:
            if DATA_USAGE in self._monitor_main[KEY_CPU][core]:
                result[DATA_BY_CORE.format(core)] = self._monitor_main[KEY_CPU][core][
                    DATA_USAGE
                ]
        if DATA_USAGE in self._monitor_main[KEY_CPU][DATA_TOTAL]:
            result[DATA_TOTAL] = self._monitor_main[KEY_CPU][DATA_TOTAL][DATA_USAGE]

        return result

    async def async_get_cpu_labels(self) -> list[str]:
        """Return list of CPU cores"""

        if self._device_cpu_cores is None:
            await self.async_monitor_main()

        result = list()
        result.append(DATA_TOTAL)
        for core in self._device_cpu_cores:
            result.append(DATA_BY_CORE.format(core))

        return result

    async def async_get_devices(self, use_cache: bool = True) -> dict[str, Any]:
        """Return device list"""

        now = datetime.utcnow()
        if (
            not self._monitor_devices.ready
            or use_cache == False
            or (
                use_cache == True
                and self._cache_time
                < (now - self._monitor_devices.time).total_seconds()
            )
        ):
            await self.async_monitor_devices()

        return self._monitor_devices.copy()

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

    async def async_get_network(
        self, use_cache: bool = True
    ) -> dict[str, (int | float)]:
        """Return traffic and speed for all interfaces"""

        now = datetime.utcnow()
        if (
            not self._monitor_main.ready
            or use_cache == False
            or (
                use_cache == True
                and self._cache_time < (now - self._monitor_main.time).total_seconds()
            )
        ):
            await self.async_monitor_main()

        result = dict()

        # Check if network was monitored
        if not self._monitor_main.ready or not KEY_NETWORK in self._monitor_main:
            return result

        for interface in self._monitor_main[KEY_NETWORK]:
            for value in self._monitor_main[KEY_NETWORK][interface]:
                result["{}_{}".format(interface, value)] = self._monitor_main[
                    KEY_NETWORK
                ][interface][value]

        return result

    async def async_get_network_labels(self) -> list[str]:
        """Return list of network interfaces"""

        if not self._monitor_main.ready:
            await self.async_monitor_main()
        if not self._identity:
            await self.async_identify()

        result = list()

        if not KEY_NETWORK in self._monitor_main:
            self._monitor_main.ready = False
            return await self.async_get_network_labels()
        for interface in self._monitor_main[KEY_NETWORK]:
            result.append(interface)

        if not "USB" in result and "dualwan" in self._identity.services:
            result.append("USB")

        return result

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

    async def async_get_ram(self, use_cache: bool = True) -> dict[str, (int | float)]:
        """Return RAM and its usage"""

        now = datetime.utcnow()
        if (
            not self._monitor_main.ready
            or use_cache == False
            or (
                use_cache == True
                and self._cache_time < (now - self._monitor_main.time).total_seconds()
            )
        ):
            await self.async_monitor_main()

        result = dict()

        # Check if RAM was monitored
        if not self._monitor_main.ready or not KEY_RAM in self._monitor_main:
            return result

        for value in self._monitor_main[KEY_RAM]:
            result[value] = self._monitor_main[KEY_RAM][value]

        return result

    async def async_get_wan(self, use_cache: bool = True) -> dict[str, str]:
        """Return WAN and its usage"""

        now = datetime.utcnow()
        if (
            not self._monitor_main.ready
            or use_cache == False
            or (
                use_cache == True
                and self._cache_time < (now - self._monitor_main.time).total_seconds()
            )
        ):
            await self.async_monitor_main()

        result = dict()

        # Check if WAN was monitored
        if not self._monitor_main.ready or not KEY_WAN in self._monitor_main:
            return result

        for value in self._monitor_main[KEY_WAN]:
            result[value] = self._monitor_main[KEY_WAN][value]

        return result

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
