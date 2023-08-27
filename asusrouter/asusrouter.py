"""AsusRouter module"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable

import aiohttp

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
    ACTION_MODE,
    AIMESH,
    APPLY,
    AR_KEY_LEDG_RGB,
    AR_KEY_LEDG_SCHEME,
    AR_KEY_LEDG_SCHEME_OLD,
    AR_LEDG_MODE,
    BOOTTIME,
    CLIENTS,
    COMMAND,
    CONST_REQUIRE_MONITOR,
    CPU,
    DEFAULT_CACHE_TIME,
    DEFAULT_TIMEOUT,
    DEVICEMAP,
    DEVICES,
    ENDHOOKS,
    ENDPOINT,
    ENDPOINTS,
    ERROR_IDENTITY,
    ERROR_VALUE,
    ETHERNET_PORTS,
    FIRMWARE,
    GWLAN,
    HD_DATA,
    HOOK,
    LED,
    LED_VAL,
    LEDG,
    LIGHT,
    MAIN,
    MAP_IDENTITY,
    MONITOR_REQUIRE_CONST,
    NETWORK,
    NVRAM,
    ONBOARDING,
    PARAM_COLOR,
    PARAM_COUNT,
    PARAM_MODE,
    PARENTAL_CONTROL,
    PORT_FORWARDING,
    PORT_STATUS,
    PORTS,
    RAM,
    RULES,
    SERVICE_COMMAND,
    SERVICE_MODIFY,
    SERVICE_REPLY,
    SERVICE_SET_LED,
    SYSINFO,
    TEMPERATURE,
    TRACK_SERVICES_LED,
    UPDATE_CLIENTS,
    VPN,
    WAN,
    WLAN,
    WLAN_TYPE,
    Merge,
)
from asusrouter.dataclass import AiMeshDevice, ConnectedDevice, PortForwarding
from asusrouter.error import AsusRouterDataProcessError
from asusrouter.util import calculators, compilers, converters, parsers, process

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
        cache_time: int = DEFAULT_CACHE_TIME,
        session: aiohttp.ClientSession | None = None,
    ):
        """Init"""

        self._host: str = host

        self._cache_time: int = cache_time

        # Monitors
        self.monitor: dict[str, Monitor] = {
            endpoint: Monitor() for endpoint in ENDPOINT
        }
        # Monitor arguments
        self.monitor_arg = {}
        for key, value in ENDHOOKS.items():
            self.monitor[key] = Monitor()
            if value:
                self.monitor_arg[key] = f"hook={compilers.hook(value)}"
            else:
                self.monitor[key].ready = False
        self._init_monitor_methods()
        self._init_monitor_requirements()
        # Constants
        self.constant = {}

        self._identity: AsusDevice | None = None
        self._ledg_color: dict[int, dict[str, int]] | None = None
        self._ledg_count: int = 0
        self._ledg_mode: int | None = None

        # State values
        self._state_led: bool = False

        # Flags
        self._flag_reboot: bool = False

        # Endpoint switch
        self._endpoint_devices: str = UPDATE_CLIENTS

        """Connect"""
        self.connection = Connection(
            host=self._host,
            username=username,
            password=password,
            port=port,
            use_ssl=use_ssl,
            session=session,
        )

    def _init_monitor_methods(self) -> None:
        """Initialize monitors"""

        self.monitor_method = {
            DEVICEMAP: self._process_monitor_devicemap,
            DEVICES: process.monitor_devices,
            ETHERNET_PORTS: process.monitor_ethernet_ports,
            FIRMWARE: self._process_monitor_firmware,
            LIGHT: process.monitor_light,
            MAIN: self._process_monitor_main,
            NVRAM: self._process_monitor_nvram,
            ONBOARDING: process.monitor_onboarding,
            PARENTAL_CONTROL: process.monitor_parental_control,
            PORT_STATUS: self._process_monitor_port_status,
            PORT_FORWARDING: process.monitor_port_forwarding,
            SYSINFO: process.monitor_sysinfo,
            TEMPERATURE: process.monitor_temperature,
            UPDATE_CLIENTS: process.monitor_update_clients,
            VPN: process.monitor_vpn,
        }

    def _init_monitor_requirements(self) -> None:
        """Initialize monitor requirements"""

        self.monitor_compile = {
            NVRAM: self._compile_monitor_nvram,
        }

    def _mark_reboot(self) -> None:
        """Mark reboot"""

        self._flag_reboot = True

    async def _check_flags(self) -> None:
        """Check flags"""

        if self._flag_reboot:
            await self.async_handle_reboot()

    # MAIN CONTROL -->

    async def async_check_endpoint(self, endpoint: str) -> bool:
        """Check if endpoint exists"""

        try:
            await self.async_api_load(endpoint)
            return True
        except (AsusRouter404, AsusRouterDataProcessError):
            return False

    async def _handle_exception(self, ex: Exception) -> None:
        """Handle exceptions raised by the connection methods."""

        raise ex

    async def async_connect(self) -> bool:
        """Connect to the device"""

        try:
            await self.connection.async_connect()
        except Exception as ex:  # pylint: disable=broad-except
            await self._handle_exception(ex)

        await self._async_identify()

        return True

    async def async_disconnect(self) -> bool:
        """Disconnect from the device"""

        try:
            await self.connection.async_disconnect()
        except Exception as ex:  # pylint: disable=broad-except
            await self._handle_exception(ex)

        return True

    async def async_drop_connection(self) -> bool:
        """Drop connection when device will not reply because of our actions"""

        try:
            await self.connection.async_drop_connection()
        except Exception as ex:  # pylint: disable=broad-except
            await self._handle_exception(ex)

        return True

    # <-- MAIN CONTROL

    # DEVICE IDENTITY -->

    async def async_get_identity(self, force: bool = False) -> AsusDevice:
        """Return device identity"""

        if not self._identity or force:
            await self._async_identify()

        return self._identity

    async def _async_identify(self) -> None:
        """Identify the device"""

        _LOGGER.debug("Identifying the device")

        # Collect data
        raw = await self._async_collect_identity()

        # Parse and save identity
        self._identity = await self._async_parse_identity(raw)

        _LOGGER.debug("Identity collected")

    async def _async_collect_identity(self) -> dict:
        """Collect identity-related data from the router's API"""

        # Compile
        query = list(MAP_IDENTITY)

        # Collect data
        message = compilers.nvram(query)
        try:
            raw = await self.async_api_hook(message)
        except Exception as ex:
            raise AsusRouterIdentityError(
                ERROR_IDENTITY.format(self._host, str(ex))
            ) from ex

        return raw

    async def _async_parse_identity(self, raw: dict) -> AsusDevice:
        """Parse identity-related data from the router's API"""

        # Process static data
        identity = process.device_identity(raw, self._host)

        # Process dynamic data
        identity[ENDPOINTS] = {}

        # Check by page
        for endpoint, address in ENDPOINT.items():
            self.monitor[endpoint].enabled = identity[ENDPOINTS][
                endpoint
            ] = await self.async_check_endpoint(address)

        # Save static values
        self._state_led = raw[LED_VAL]

        # Define usable endpoints
        if identity["firmware"].minor == 380:
            self._endpoint_devices = DEVICES

        return AsusDevice(**identity)

    # <-- DEVICE IDENTITY

    # API COMMUNICATIONS -->

    async def async_api_command(
        self,
        commands: dict[str, str] | None = None,
        endpoint: str = ENDPOINT[COMMAND],
    ) -> dict[str, Any]:
        """Send a command to API"""

        return await self.async_api_load(endpoint=endpoint, command=str(commands))

    async def async_api_hook(self, hook: str | None = None) -> dict[str, Any]:
        """Hook data from API"""

        return await self.async_api_load(
            endpoint=ENDPOINT[HOOK],
            command=f"{HOOK}={hook}",
        )

    async def async_api_load(
        self,
        endpoint: str | None = None,
        command: str = "",
    ) -> dict[str, Any]:
        """Load API endpoint"""

        # Endpoint should be selected
        if endpoint is None:
            _LOGGER.debug("No endpoint selected")
            return {}

        # Process endpoint
        try:
            result = await self.connection.async_run_command(
                command=command, endpoint=endpoint
            )
        # HTTP 404 should be processed separately
        except AsusRouter404 as ex:
            raise AsusRouter404 from ex
        except Exception as ex:
            raise ex

        # Check for errors during API call
        if self.connection.error:
            _LOGGER.debug("Error flag found. Fixing")
            await self._async_handle_error()

        return result

    # <-- API COMMUNICATIONS

    # MONITORS -->

    async def async_monitor(self, endpoint: str) -> None:
        """Monitor an endpoint"""

        # Check flags before monitoring for new data
        await self._check_flags()

        # Check whether to run
        if not await self.async_monitor_should_run(endpoint):
            return

        processor: Callable[[str], dict[str, Any]] = self.monitor_method.get(endpoint)

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
            result = processor(raw, time=monitor.time)
            for key, data in result.items():
                monitor[key] = data

            # Finish and save data
            monitor.finish()
            self.monitor[endpoint] = monitor

        except AsusRouterError as ex:
            self.monitor[endpoint].drop()
            raise ex

        return

    async def async_monitor_available(self, monitor: str) -> bool:
        """Check whether monitor is available"""

        # Monitor does not exist
        if monitor not in self.monitor:
            _LOGGER.debug("Monitor `%s` does not exist", monitor)
            return False

        # Monitor is disabled
        if not self.monitor[monitor].enabled:
            _LOGGER.debug("Monitor `%s` is disabled", monitor)
            return False

        _LOGGER.debug("Monitor `%s` is enabled", monitor)
        return True

    async def async_monitor_cached(self, monitor: str, value: Any) -> bool:
        """Check whether monitor has cached value"""

        if (
            not self.monitor[monitor].ready
            or value not in self.monitor[monitor]
            or self._cache_time
            < (datetime.utcnow() - self.monitor[monitor].time).total_seconds()
        ):
            _LOGGER.debug(
                "Value `%s` is not in cache yet by monitor `%s` "
                "or the caching time has already expired",
                value,
                monitor,
            )
            return False

        _LOGGER.debug(
            "Value `%s` is already cached by monitor `%s`. Using cache", value, monitor
        )
        return True

    async def async_monitor_ready(self, monitor: str, retry=False) -> bool:
        """Get monitor ready to run"""

        if not self.monitor[monitor].ready:
            requirement = MONITOR_REQUIRE_CONST.get(monitor)
            if requirement:
                value = self.constant.get(requirement)
                if value:
                    _LOGGER.debug(
                        "Required constant found. Trying to compile monitor `%s`",
                        monitor,
                    )
                    self.monitor_compile[monitor](value)
                    return True
                if not retry and requirement in CONST_REQUIRE_MONITOR:
                    _LOGGER.debug(
                        "Monitor `%s` requires constant `%s` to be found first. "
                        "Initializing corresponding monitor",
                        monitor,
                        requirement,
                    )
                    await self.async_monitor(CONST_REQUIRE_MONITOR[requirement])
                    return await self.async_monitor_ready(monitor, retry=True)
                return False
            return False
        return True

    async def async_monitor_should_run(self, monitor: str) -> bool:
        """Check whether monitor should be run"""

        # Monitor is not available
        if not await self.async_monitor_available(monitor):
            return False

        # Monitor not ready
        if not await self.async_monitor_ready(monitor):
            return False

        # Monitor is already running - wait to complete
        if self.monitor[monitor].active:
            try:
                await asyncio.wait_for(
                    self.monitor[monitor].inactive_event.wait(), timeout=DEFAULT_TIMEOUT
                )
            except asyncio.TimeoutError:
                return False
            return False

        return True

    # COMPILE MONITORS

    def _compile_monitor_nvram(self, wlan: list[str]) -> None:
        """Compile `nvram` monitor"""

        _LOGGER.debug("Compiling monitor NVRAM")

        arg = compilers.monitor_arg_nvram(wlan)
        if arg:
            self.monitor_arg[NVRAM] = f"hook={arg}"
        self.monitor[NVRAM].ready = True

        _LOGGER.debug("Monitor NVRAM was compiled")

    # PROCESS MONITORS

    def _process_monitor_devicemap(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `devicemap` endpoint"""

        # Devicemap
        devicemap = raw

        # Boot time
        boottime, reboot = process.data_boottime(
            devicemap, self.monitor[DEVICEMAP].get(BOOTTIME)
        )

        # Mark reboot
        if reboot:
            self._mark_reboot()

        # VPN
        vpn = process.data_vpn(devicemap)

        return {
            DEVICEMAP: devicemap,
            BOOTTIME: boottime,
            VPN: vpn,
        }

    def _process_monitor_firmware(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `firmware` endpoint"""

        # Firmware
        firmware = process.data_firmware(raw, self._identity.firmware)

        return {
            FIRMWARE: firmware,
        }

    def _process_monitor_main(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `main` endpoint.

        This endpoint combines CPU, RAM, network and WAN data
        which can be received with a single request.
        This way we avoid quering small pieces of data separately."""

        monitor_ready = self.monitor[MAIN].ready

        # CPU
        prev_cpu = self.monitor[MAIN].get(CPU) if monitor_ready else {}
        cpu_usage = raw.get("cpu_usage")
        cpu = process.data_cpu(cpu_usage, prev_cpu) if cpu_usage else prev_cpu

        # RAM
        prev_ram = self.monitor[MAIN].get(RAM) if monitor_ready else {}
        memory_usage = raw.get("memory_usage")
        ram = process.data_ram(memory_usage) if memory_usage else prev_ram

        # Network
        prev_network = self.monitor[MAIN].get(NETWORK) if monitor_ready else {}
        time_delta = (
            (time - self.monitor[MAIN].time).total_seconds() if prev_network else None
        )
        netdev = raw.get("netdev")
        network = (
            process.data_network(netdev, prev_network, time_delta)
            if netdev
            else prev_network
        )

        # Check for the USB interface
        # Checking identity should always be safe
        # since we are obtaining it before any other request to the device
        if "usb" not in network and "dualwan" in self._identity.services:
            network["usb"] = {}

        # Save network constant
        constant = [interface for interface in network if interface in WLAN_TYPE]
        self._init_constant(WLAN, constant)

        # WAN
        prev_wan = self.monitor[MAIN].get(WAN) if monitor_ready else {}
        wanlink_state = raw.get("wanlink_state")
        wan = process.data_wan(wanlink_state) if wanlink_state else prev_wan

        return {
            CPU: cpu,
            NETWORK: network,
            RAM: ram,
            WAN: wan,
        }

    def _process_monitor_nvram(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `nvram` endpoint"""

        available_wlan = self.constant[WLAN]
        wlan, gwlan = process.data_wlan(raw, available_wlan)

        return {
            GWLAN: gwlan,
            WLAN: wlan,
        }

    def _process_monitor_port_status(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `port status` endpoint"""

        prev_ports = (
            self.monitor[PORT_STATUS].get(PORTS)
            if self.monitor[PORT_STATUS].ready
            else None
        )
        port_info = raw.get("port_info")
        ports = (
            process.data_port_status(raw, self._identity.mac)
            if port_info
            else prev_ports
        )

        return {
            PORTS: ports,
        }

    # <-- MONITORS

    # TECHNICAL -->

    async def _async_handle_error(self) -> None:
        """Actions to be taken on connection error"""

        # Drop history dependent monitor values
        for monitor, data in HD_DATA:
            if monitor in self.monitor and data in self.monitor[monitor]:
                self.monitor[monitor].pop(data)

        # Clear error flag
        await self.connection.async_reset_error()

        return

    def _init_constant(self, constant: str, value: Any) -> None:
        """Initialize constant if not initialized yet"""

        # Check that constant is not assigned yet
        if constant in self.constant:
            return

        # Assign constant
        _LOGGER.debug("Initializing constant `%s`=`%s`", constant, value)
        self.constant[constant] = value

    # <-- TECHNICAL

    async def async_handle_reboot(self) -> None:
        """Actions to be taken on reboot"""

        # Handle reboot as error
        await self._async_handle_error()

        # Recover LED state
        await self.async_keep_state_led()
        self._flag_reboot = False

        return

    # PROCESS DATA -->

    def _process_data_none(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Don't process the data"""

        return raw

    # <-- PROCESS DATA

    # RETURN DATA -->

    async def async_get_data(
        self,
        data: str,
        monitor: str | list[str],
        merge: Merge = Merge.ANY,
        processor: Callable[[str], dict[str, Any]] | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Return data from the first available monitor in the list"""

        result = {}

        # Convert to list if only one monitor is set
        monitor = [monitor] if isinstance(monitor, str) else monitor

        # Create a list of available monitors
        monitors = [
            item for item in monitor if await self.async_monitor_available(item)
        ]

        # Check if any monitors are available
        if not monitors:
            return {}

        # In this mode we need only one of the monitors
        if merge == Merge.ANY:
            monitors = monitors[:1]

        # Process monitors
        for _monitor in monitors:
            # Value is not cached or cache is disabled
            if not await self.async_monitor_cached(_monitor, data) or not use_cache:
                await self.async_monitor(_monitor)

            # Receive data
            part = self.monitor[_monitor].get(data or {})

            # Update data
            compilers.update_rec(result, part)

        # Process data
        if processor:
            result = processor(result)

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

    async def async_get_connected_devices(
        self, use_cache: bool = True
    ) -> dict[str, ConnectedDevice]:
        """Return connected devices data"""

        return await self.async_get_data(
            data=CLIENTS,
            monitor=[self._endpoint_devices, ONBOARDING],
            merge=Merge.ALL,
            use_cache=use_cache,
            processor=process.data_connected_devices,
        )

    async def async_get_cpu(self, use_cache: bool = True) -> dict[str, float]:
        """Return CPU data"""

        return await self.async_get_data(data=CPU, monitor=MAIN, use_cache=use_cache)

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

    async def async_get_gwlan(self, use_cache: bool = True) -> dict[str, Any]:
        """Return GWLAN data"""

        return await self.async_get_data(data=GWLAN, monitor=NVRAM, use_cache=use_cache)

    async def async_get_led(self, use_cache: bool = True) -> dict[str, Any]:
        """Return LED data"""

        return await self.async_get_data(data=LED, monitor=LIGHT, use_cache=use_cache)

    async def async_get_network(
        self, use_cache: bool = True
    ) -> dict[str, (int | float)]:
        """Return network data"""

        return await self.async_get_data(
            data=NETWORK, monitor=MAIN, use_cache=use_cache
        )

    async def async_get_parental_control(
        self, use_cache: bool = True
    ) -> dict[str, (int | float)]:
        """Return parental control data"""

        return await self.async_get_data(
            data=PARENTAL_CONTROL, monitor=PARENTAL_CONTROL, use_cache=use_cache
        )

    async def async_get_port_forwarding(self, use_cache: bool = True) -> dict[str, Any]:
        """Return port forwarding data"""

        return await self.async_get_data(
            data=PORT_FORWARDING, monitor=PORT_FORWARDING, use_cache=use_cache
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

    async def async_get_wlan(self, use_cache: bool = True) -> dict[str, Any]:
        """Return WLAN data"""

        return await self.async_get_data(data=WLAN, monitor=NVRAM, use_cache=use_cache)

    # <-- RETURN DATA

    # APPLY -->

    # LED
    async def async_set_led(self, value: bool | int | str) -> bool:
        """Set LED state"""

        value_to_set = converters.bool_from_any(value)

        service = SERVICE_SET_LED
        arguments = {
            LED_VAL: converters.int_from_bool(value_to_set),
        }

        result = await self.async_service_generic_apply(
            service=service, arguments=arguments
        )

        if result:
            self._state_led = value_to_set
        return result

    # Parental control
    async def async_apply_parental_control_rules(
        self,
        rules: dict[str, FilterDevice],
    ) -> bool:
        """Apply parental control rules"""

        request = compilers.parental_control(rules)

        return await self.async_service_generic_apply(
            service="restart_firewall",
            arguments=request,
        )

    async def async_remove_parental_control_rules(
        self,
        macs: str | list[str] | None = None,
        rules: FilterDevice | list[FilterDevice] = None,
        apply: bool = True,
    ) -> dict[str, FilterDevice]:
        """Remove parental control rules"""

        macs = set() if macs is None else set(converters.as_list(macs))
        rules = [] if rules is None else converters.as_list(rules)

        # Get current rules
        current_rules: dict = (await self.async_get_parental_control())[RULES]

        # Remove old rules for these MACs
        for mac in macs:
            current_rules.pop(mac, None)
        for rule in rules:
            current_rules.pop(rule.mac, None)

        # Apply new rules
        if apply:
            await self.async_apply_parental_control_rules(current_rules)

        # Return the new rules
        return current_rules

    async def async_set_parental_control_rules(
        self,
        rules: FilterDevice | list[FilterDevice],
    ) -> bool:
        """Set parental control rules"""

        rules = converters.as_list(rules)

        # Remove old rules for these MACs and get the rest of the list
        current_rules = await self.async_remove_parental_control_rules(
            rules, apply=False
        )

        # Add new rules
        for rule in rules:
            current_rules[rule.mac] = rule

        # Apply new rules
        return await self.async_apply_parental_control_rules(current_rules)

    # Port forwarding
    async def async_apply_port_forwarding_rules(
        self,
        rules: list[PortForwarding],
    ) -> bool:
        """Apply port forwarding rules"""

        request = compilers.port_forwarding(rules)

        return await self.async_service_generic_apply(
            service="restart_firewall",
            arguments=request,
        )

    async def async_remove_port_forwarding_rules(
        self,
        ips: str | list[str] | None = None,
        rules: PortForwarding | list[PortForwarding] | None = None,
        apply: bool = True,
    ) -> list[PortForwarding]:
        """Remove port forwarding rules"""

        ips = set() if ips is None else set(converters.as_list(ips))
        rules = [] if rules is None else converters.as_list(rules)

        # Get current rules
        current_rules: list[PortForwarding] = (await self.async_get_port_forwarding())[
            RULES
        ]

        # Remove all rules for these IPs
        current_rules = [rule for rule in current_rules if rule.ip not in ips]
        # Remove exact rules
        for rule_to_find in rules:
            current_rules = [
                rule
                for rule in current_rules
                if not (
                    rule.ip == rule_to_find.ip
                    and rule.port_external == rule_to_find.port_external
                    and rule.protocol == rule_to_find.protocol
                    and (
                        rule_to_find.ip_external is None
                        or rule.ip_external == rule_to_find.ip_external
                    )
                    and (rule_to_find.port is None or rule.port == rule_to_find.port)
                )
            ]

        # Apply new rules
        if apply:
            await self.async_apply_port_forwarding_rules(current_rules)

        # Return the new rules
        return current_rules

    async def async_set_port_forwarding_rules(
        self,
        rules: PortForwarding | list[PortForwarding],
    ) -> bool:
        """Set port forwarding rules"""

        rules = converters.as_list(rules)

        # Get current rules
        current_rules: list[PortForwarding] = (await self.async_get_port_forwarding())[
            RULES
        ]

        # Add new rules
        for rule in rules:
            current_rules.append(rule)

        # Apply new rules
        return await self.async_apply_port_forwarding_rules(current_rules)

    # <-- APPLY

    # SERVICE -->

    async def async_service_generic(
        self,
        service: str,
        arguments: dict[str, Any] | None = None,
        expect_modify: bool = True,
        drop_connection: bool = False,
    ) -> bool:
        """Run generic service"""

        # Generate commands
        # Should include service name to run and default mode to apply changes
        commands = {
            SERVICE_COMMAND: service,
        }

        # Add arguments if any
        if arguments:
            commands.update(arguments)

        # Try running the service command
        try:
            result = await self.async_api_command(commands=commands)
        except AsusRouterServerDisconnectedError as ex:
            if drop_connection:
                _LOGGER.debug(
                    "Service `%s` requires dropping connection to the device", service
                )
                await self.async_drop_connection()
                return True
            raise ex

        # Check for the run success
        if (
            SERVICE_REPLY not in result
            or result[SERVICE_REPLY] != service
            or SERVICE_MODIFY not in result
        ):
            raise AsusRouterServiceError(
                f"Something went wrong running service `{service}`."
                f"Raw result is: {result}"
            )
        _LOGGER.debug(
            "Service `%s` was run successfully with arguments`%s`. Result: %s",
            service,
            arguments,
            result,
        )

        # Check whether service(s) run requires additional actions
        services = service.split(";")
        if any(service in TRACK_SERVICES_LED for service in services):
            await self.async_keep_state_led()

        # Return based on the expectations
        if expect_modify:
            return converters.bool_from_any(result[SERVICE_MODIFY])
        return True

    async def async_service_generic_apply(
        self,
        service: str,
        arguments: dict[str, Any] | None = None,
        expect_modify: bool = True,
        drop_connection: bool = False,
    ) -> bool:
        """Run generic service with apply"""

        if not arguments:
            arguments = {ACTION_MODE: APPLY}
        else:
            arguments[ACTION_MODE] = APPLY

        return await self.async_service_generic(
            service=service,
            arguments=arguments,
            expect_modify=expect_modify,
            drop_connection=drop_connection,
        )

    # <-- SERVICE

    # ALPHA / NOT READY -->

    async def async_service_ledg_get(self) -> dict[str, Any] | None:
        """Return status of RGB LEDs in LEDG scheme"""

        nvram = [AR_KEY_LEDG_RGB.format(mode) for mode in AR_LEDG_MODE]
        nvram.extend([AR_KEY_LEDG_SCHEME, AR_KEY_LEDG_SCHEME_OLD])

        data = await self.async_api_hook(compilers.nvram(nvram))

        ledg = {}
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

        if mode not in AR_LEDG_MODE:
            raise (AsusRouterValueError(ERROR_VALUE.format(mode)))

        # Check for the known state
        if not self._ledg_mode or not self._ledg_color:
            await self.async_service_ledg_get()

        colors = calculators.rgb(color)
        colors.update(
            {
                num: self._ledg_color[num]
                for num in range(1, self._ledg_count + 1)
                if num not in colors and self._ledg_color and num in self._ledg_color
            }
        )

        color_to_set = compilers.rgb(colors)

        result = await self.async_api_load(
            f"{ENDPOINT[LEDG]}?{AR_KEY_LEDG_SCHEME}" f"={mode}&ledg_rgb={color_to_set}"
        )

        if "statusCode" in result and int(result["statusCode"]) == 200:
            return True

        return False

    # <-- ALPHA / NOT READY

    async def async_keep_state_led(self) -> bool:
        """Keep state of LEDs"""

        # Only for Merlin firmware, so sysinfo should be present
        if self._identity.endpoints.get(SYSINFO) and self.state_led is False:
            await self.async_set_led(True)
            await self.async_set_led(False)

    @property
    def connected(self) -> bool:
        """Connection status"""
        return self.connection.connected

    @property
    def state_led(self) -> bool:
        """LED status"""
        return self._state_led

    @property
    def ledg_count(self) -> int:
        """LEDG status"""
        return self._ledg_count
