"""AsusRouter module"""

from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)

import asyncio
from datetime import datetime
from typing import Any

from asusrouter import (
    AsusDevice,
    AsusRouter404,
    AsusRouterIdentityError,
    AsusRouterServerDisconnectedError,
    AsusRouterServiceError,
    AsusRouterValueError,
    Connection,
    Monitor,
)
from asusrouter.const import (
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
    AR_KEY_RAM,
    AR_KEY_SERVICE_COMMAND,
    AR_KEY_SERVICE_MODIFY,
    AR_KEY_SERVICE_REPLY,
    AR_KEY_VPN_CLIENT,
    AR_KEY_WAN,
    AR_LEDG_MODE,
    AR_PATH,
    AR_SERVICE_COMMAND,
    AR_SERVICE_CONTROL,
    AR_SERVICE_DROP_CONNECTION,
    DATA_BY_CORE,
    DATA_TOTAL,
    DATA_USAGE,
    DATA_USED,
    DEFAULT_ACTION_MODE,
    DEFAULT_CACHE_TIME,
    DEFAULT_SLEEP_TIME,
    ERROR_IDENTITY,
    ERROR_SERVICE,
    ERROR_SERVICE_UNKNOWN,
    ERROR_VALUE,
    INTERFACE_TYPE,
    KEY_ACTION_MODE,
    KEY_CPU,
    KEY_HOOK,
    KEY_NETWORK,
    KEY_RAM,
    KEY_SYSINFO,
    KEY_TEMPERATURE,
    KEY_VPN,
    KEY_WAN,
    MONITOR_MAIN,
    MSG_ERROR,
    MSG_INFO,
    MSG_SUCCESS,
    NVRAM_LIST,
    PARAM_COLOR,
    PARAM_COUNT,
    PARAM_MODE,
    PORT_TYPE,
)
from asusrouter.util import calculators, compilers, converters, parsers


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
    ):
        """Init"""

        self._host: str = host

        self._cache_time: int = cache_time
        self._enable_monitor: bool = enable_monitor
        self._enable_control: bool = enable_control

        self._device_cpu_cores: list[int] | None = None
        self._device_ports: dict[str, str] | None = None
        self._device_boottime: datetime | None = None

        self._monitor_main: Monitor = Monitor()
        self._monitor_nvram: Monitor = Monitor()
        self._monitor_misc: Monitor = Monitor()
        self._monitor_devices: Monitor = Monitor()

        self._identity: AsusDevice | None = None
        self._ledg_color: dict[int, dict[str, int]] | None = None
        self._ledg_count: int = 0
        self._ledg_mode: int | None = None
        self._status_led: bool = False

        """Connect"""
        self.connection = Connection(
            host=self._host,
            username=username,
            password=password,
            port=port,
            use_ssl=use_ssl,
            cert_check=cert_check,
            cert_path=cert_path,
        )

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
            AsusRouterIdentityError(ERROR_IDENTITY.format(self._host, str(ex)))

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
                AsusRouterIdentityError(ERROR_IDENTITY.format(self._host, str(ex)))

        # Check by page
        identity["sysinfo"] = await self.async_check_endpoint(
            endpoint=AR_PATH["sysinfo"]
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

        # Check VPN
        try:
            data = await self.connection.async_load(AR_PATH["vpn"])
            identity["vpn_status"] = True
        except AsusRouter404 as ex:
            """Do nothing"""

        # Save static values
        self._status_led = raw[AR_KEY_LED]

        self._identity = AsusDevice(**identity)

        _LOGGER.debug(MSG_SUCCESS["identity"])

    ### <-- MAIN CONTROL

    ### DATA PROCESSING -->

    async def async_command(
        self, commands: dict[str, str], action_mode: str = DEFAULT_ACTION_MODE
    ) -> dict[str, Any]:
        """Command device to run a service or set parameter"""

        result = {}

        if not self._enable_control:
            _LOGGER.error(MSG_ERROR["disabled_control"])
            return result

        request: dict = {
            KEY_ACTION_MODE: action_mode,
        }
        for command in commands:
            request[command] = commands[command]

        try:
            result = await self.connection.async_run_command(
                command=str(request), endpoint=AR_PATH["command"]
            )
            _LOGGER.debug("{}: {}".format(MSG_SUCCESS["command"], request))
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
            _LOGGER.debug("{}: {}".format(MSG_SUCCESS["hook"], hook))
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
            _LOGGER.debug(MSG_SUCCESS["load"].format(page))
        except AsusRouter404 as ex:
            raise ex
        except Exception as ex:
            _LOGGER.error(ex)

        return result

    ### <-- DATA PROCESSING

    ### MONITORS -->

    async def async_monitor_main(self) -> None:
        """Get all the main monitor values. Non-cacheable"""

        while self._monitor_main.active:
            _LOGGER.debug(MSG_INFO["monitor_sleep"].format("main"))
            await asyncio.sleep(DEFAULT_SLEEP_TIME)
            _LOGGER.debug(MSG_INFO["monitor_wakeup"].format("main"))
            return

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
            monitor_main[KEY_NETWORK] = parsers.network_usage(raw=data[AR_KEY_NETWORK])

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

        ### SYSINFO ###

        if self._identity:
            if self._identity.sysinfo:
                monitor_main[KEY_SYSINFO] = await self.async_load(
                    page=AR_PATH["sysinfo"]
                )

        monitor_main.finish()
        self._monitor_main = monitor_main

        return

    async def async_monitor_nvram(self, groups: list[str] | str | None = None) -> None:
        """Get the NVRAM values for the specified group list"""

        while self._monitor_nvram.active:
            _LOGGER.debug(MSG_INFO["monitor_sleep"].format("nvram"))
            await asyncio.sleep(DEFAULT_SLEEP_TIME)
            _LOGGER.debug(MSG_INFO["monitor_wakeup"].format("nvram"))
            return

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
                _LOGGER.warning("There is no {} in known NVRAM groups".format(group))

        message = compilers.nvram(requests)
        result = await self.async_hook(message)

        monitor_nvram.reset()

        for item in result:
            monitor_nvram[item] = result[item]

        monitor_nvram.finish()
        self._monitor_nvram = monitor_nvram

        return

    async def async_monitor_misc(self) -> None:
        """Get all other useful values"""

        while self._monitor_misc.active:
            _LOGGER.debug(MSG_INFO["monitor_sleep"].format("misc"))
            await asyncio.sleep(DEFAULT_SLEEP_TIME)
            _LOGGER.debug(MSG_INFO["monitor_wakeup"].format("misc"))
            return

        self._monitor_misc.start()

        monitor_misc = Monitor()

        ### PORTS

        # Receive ports number and status (disconnected, 100 Mb/s, 1 Gb/s)
        data = await self.async_load(page=AR_PATH["ports"])

        monitor_misc.reset()

        monitor_misc["PORTS"] = dict()
        if "portSpeed" in data:
            for type in PORT_TYPE:
                monitor_misc["PORTS"][type] = dict()
            for value in data["portSpeed"]:
                for type in PORT_TYPE:
                    if type in value:
                        number = value.replace(type, "")
                        monitor_misc["PORTS"][type][number] = parsers.port_speed(
                            data["portSpeed"][value]
                        )
                        break

        ### TEMPERATURES ###
        monitor_misc[KEY_TEMPERATURE] = await self.async_load(
            page=AR_PATH["temperature"]
        )

        # Load devicemap
        data = await self.async_load(page=AR_PATH["devicemap"])
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

        # Calculate boot time. Since precision is 1 second, could be that old and new are 1 sec different. In this case, we should not change the boot time, but keep the previous value to avoid regular changes
        if "SYS" in monitor_misc["DEVICEMAP"]:
            if "uptimeStr" in monitor_misc["DEVICEMAP"]["SYS"]:
                time = parsers.uptime(monitor_misc["DEVICEMAP"]["SYS"]["uptimeStr"])
                timestamp = int(time.timestamp())
                if not "BOOTTIME" in monitor_misc:
                    monitor_misc["BOOTTIME"] = dict()

                if "BOOTTIME" in self._monitor_misc:
                    _timestamp = self._monitor_misc["BOOTTIME"]["timestamp"]
                    _time = datetime.fromtimestamp(_timestamp)
                    if time == _time or abs(timestamp - _timestamp) < 2:
                        monitor_misc["BOOTTIME"] = self._monitor_misc["BOOTTIME"]
                    # This happens on reboots if data is checked before the device got correct time from NTP
                    elif timestamp - _timestamp < 0:
                        # Leave the same boot time, since we don't know the new correct time
                        monitor_misc["BOOTTIME"] = self._monitor_misc["BOOTTIME"]
                    else:
                        monitor_misc["BOOTTIME"]["timestamp"] = timestamp
                        monitor_misc["BOOTTIME"]["ISO"] = time.isoformat()
                else:
                    monitor_misc["BOOTTIME"]["timestamp"] = timestamp
                    monitor_misc["BOOTTIME"]["ISO"] = time.isoformat()

                if self._device_boottime != monitor_misc["BOOTTIME"]["ISO"]:
                    self._device_boottime = monitor_misc["BOOTTIME"]["ISO"]

        monitor_misc.finish()
        self._monitor_misc = monitor_misc

        return

    async def async_monitor_devices(self) -> None:
        """Monitor connected devices"""

        while self._monitor_devices.active:
            _LOGGER.debug(MSG_INFO["monitor_sleep"].format("devices"))
            await asyncio.sleep(DEFAULT_SLEEP_TIME)
            _LOGGER.debug(MSG_INFO["monitor_wakeup"].format("devices"))
            return

        self._monitor_devices.start()
        monitor_devices = Monitor()

        data = await self.async_hook(AR_HOOK_DEVICES)
        monitor_devices.reset()

        # Search for new data
        if AR_KEY_DEVICES in data:
            data = data[AR_KEY_DEVICES]
            for mac in data:
                if converters.is_mac_address(mac):
                    monitor_devices[mac] = parsers.connected_device(data[mac])
        # Or keep last data
        elif self._monitor_devices.ready:
            monitor_devices = self._monitor_devices

        monitor_devices.finish()
        self._monitor_devices = monitor_devices

        return

    ### <-- MONITORS

    async def async_handle_error(self) -> None:
        """Actions to be taken on connection errors"""

        # Most of errors come from device reboots. Handle it
        await self.async_handle_reboot()

        # Clear error
        await self.connection.async_reset_error()

        return

    async def async_handle_reboot(self) -> None:
        """Actions to be taken on reboot"""

        # Clear main monitor to prevent calculation errors in it
        if self._monitor_main.ready:
            self._monitor_main = Monitor()

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

    ### RETURN DATA -->

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

    async def async_get_devicemap(self, use_cache: bool = True) -> dict[str, Any]:
        """Return devicemap"""

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
            await self.async_monitor_misc()

        return self._monitor_misc["DEVICEMAP"]

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

        for interface in self._monitor_main[KEY_NETWORK]:
            result.append(interface)

        if not "USB" in result and "dualwan" in self._identity.services:
            result.append("USB")

        return result

    async def async_get_ports(
        self, use_cache: bool = True
    ) -> dict[str, dict[str, int]]:
        """Return WAN/LAN ports status"""

        now = datetime.utcnow()
        if (
            not self._monitor_misc.ready
            or use_cache == False
            or (
                use_cache == True
                and self._cache_time < (now - self._monitor_misc.time).total_seconds()
            )
        ):
            await self.async_monitor_misc()

        return self._monitor_misc["PORTS"]

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

    async def async_get_ram_labels(self) -> list[str]:
        """Return list of CPU cores"""

        if not self._monitor_main.ready:
            await self.async_monitor_main()

        result = list()
        for value in self._monitor_main[KEY_RAM]:
            result.append(value)

        return result

    async def async_get_sysinfo(self, use_cache: bool = True) -> dict[str, Any]:
        """Return sysinfo status"""

        if not self._identity.sysinfo:
            return {}

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

        if not KEY_SYSINFO in self._monitor_main:
            return {}

        return self._monitor_main[KEY_SYSINFO]

    async def async_get_temperature(self, use_cache: bool = True) -> dict[str, Any]:
        """Raturn temperature status"""

        now = datetime.utcnow()
        if (
            not self._monitor_misc.ready
            or use_cache == False
            or (
                use_cache == True
                and self._cache_time < (now - self._monitor_misc.time).total_seconds()
            )
        ):
            await self.async_monitor_misc()

        return self._monitor_misc[KEY_TEMPERATURE]

    async def async_get_temperature_labels(self) -> list[str]:
        """Return list of temperature sensors"""

        if not self._monitor_misc.ready:
            await self.async_monitor_misc()

        result = list()
        for value in self._monitor_misc[KEY_TEMPERATURE]:
            result.append(value)

        return result

    async def async_get_vpn(self, use_cache: bool = True) -> dict[str, Any]:
        """Return VPN status"""

        now = datetime.utcnow()
        if (
            not self._monitor_misc.ready
            or use_cache == False
            or (
                use_cache == True
                and self._cache_time < (now - self._monitor_misc.time).total_seconds()
            )
        ):
            await self.async_monitor_misc()

        return self._monitor_misc[KEY_VPN]

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

    async def async_service_reboot(self) -> bool:
        """Reboot the device"""

        service = "reboot"
        await self.async_service_run(service=service, drop_connection=True)
        return True

    ### <-- SERVICES

    @property
    def connected(self) -> bool:
        return self.connection.connected

    @property
    def boottime(self) -> datetime:
        return self._device_boottime

    @property
    def led(self) -> bool:
        return self._status_led

    @property
    def ledg_count(self) -> int:
        return self._ledg_count
