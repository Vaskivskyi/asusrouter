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
    CLIENTS_HISTORIC,
    COMMAND,
    CONNECTION_TYPE,
    CONST_REQUIRE_MONITOR,
    CONVERTERS,
    CPU,
    CPU_USAGE,
    DEFAULT_CACHE_TIME,
    DEFAULT_SLEEP_TIME,
    DELIMITER_PARENTAL_CONTROL_ITEM,
    DEVICEMAP,
    DEVICES,
    ENDHOOKS,
    ENDPOINT,
    ENDPOINTS,
    ERRNO,
    ERROR_IDENTITY,
    ERROR_VALUE,
    ETHERNET_PORTS,
    FIRMWARE,
    GUEST,
    GWLAN,
    HD_DATA,
    HOOK,
    INFO,
    IP,
    ISO,
    KEY_PARENTAL_CONTROL_MAC,
    KEY_PARENTAL_CONTROL_STATE,
    KEY_PARENTAL_CONTROL_TYPE,
    LAN,
    LED,
    LED_VAL,
    LEDG,
    LIGHT,
    LINK_RATE,
    MAC,
    MAIN,
    MAP_CONNECTED_DEVICE,
    MAP_IDENTITY,
    MAP_NVRAM,
    MAP_OVPN_STATUS,
    MAP_PARENTAL_CONTROL_ITEM,
    MAP_PARENTAL_CONTROL_TYPE,
    MEMORY_USAGE,
    MONITOR_REQUIRE_CONST,
    NAME,
    NETDEV,
    NETWORK,
    NODE,
    NVRAM,
    ONBOARDING,
    ONLINE,
    PARAM_COLOR,
    PARAM_COUNT,
    PARAM_MODE,
    PARENTAL_CONTROL,
    PORT,
    PORT_STATUS,
    PORT_TYPES,
    PORTS,
    RAM,
    RANGE_GWLAN,
    RANGE_OVPN_CLIENTS,
    RSSI,
    RULES,
    SERVICE_COMMAND,
    SERVICE_MODIFY,
    SERVICE_REPLY,
    SERVICE_SET_LED,
    SPEED_TYPES,
    STATE,
    STATUS,
    SYS,
    SYSINFO,
    TEMPERATURE,
    TIMEMAP,
    TIMESTAMP,
    TOTAL,
    TRACK_SERVICES_LED,
    TYPE,
    UNKNOWN,
    UPDATE_CLIENTS,
    USB,
    USED,
    VPN,
    VPN_CLIENT,
    WAN,
    WANLINK_STATE,
    WLAN,
    WLAN_TYPE,
    Merge,
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
            DEVICES: self._process_monitor_devices,
            ETHERNET_PORTS: self._process_monitor_ethernet_ports,
            FIRMWARE: self._process_monitor_firmware,
            LIGHT: self._process_monitor_light,
            MAIN: self._process_monitor_main,
            NVRAM: self._process_monitor_nvram,
            ONBOARDING: self._process_monitor_onboarding,
            PARENTAL_CONTROL: self._process_monitor_parental_control,
            PORT_STATUS: self._process_monitor_port_status,
            SYSINFO: self._process_monitor_sysinfo,
            TEMPERATURE: self._process_monitor_temperature,
            UPDATE_CLIENTS: self._process_monitor_update_clients,
            VPN: self._process_monitor_vpn,
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

        _LOGGER.debug("Identifying the device")

        # Compile
        query = []
        for item in MAP_IDENTITY:
            query.append(item)

        # Collect data
        message = compilers.nvram(query)
        try:
            raw = await self.async_api_hook(message)
        except Exception as ex:
            raise AsusRouterIdentityError(
                ERROR_IDENTITY.format(self._host, str(ex))
            ) from ex

        # Parse
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
                raise AsusRouterIdentityError(
                    ERROR_IDENTITY.format(self._host, str(ex))
                ) from ex

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

        # Save identity
        self._identity = AsusDevice(**identity)

        _LOGGER.debug("Identity collected")

    # <-- MAIN CONTROL

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

        now = datetime.utcnow()
        if (
            not self.monitor[monitor].ready
            or value not in self.monitor[monitor]
            or self._cache_time < (now - self.monitor[monitor].time).total_seconds()
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
            while self.monitor[monitor].active:
                await asyncio.sleep(DEFAULT_SLEEP_TIME)
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
        boottime = {}
        # Since precision is 1 second, could be that old and new are 1 sec different.
        # In this case, we should not change the boot time,
        # but keep the previous value to avoid regular changes
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
        vpn = {}
        vpnmap = devicemap.get(VPN)
        if vpnmap:
            for num in RANGE_OVPN_CLIENTS:
                key = f"{VPN_CLIENT}{num}"
                vpn[key] = {}
                if f"{key}_{STATE}" in vpnmap:
                    status = converters.int_from_str(vpnmap[f"{key}_{STATE}"])
                    vpn[key][STATE] = status > 0
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

    def _process_monitor_devices(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `devices` endpoint"""

        # Clients
        clients = {}
        if "get_clientlist" in raw:
            data = raw["get_clientlist"]
            for mac, description in data.items():
                if converters.is_mac_address(mac):
                    clients[mac] = description

        return {
            CLIENTS: clients,
        }

    def _process_monitor_ethernet_ports(
        self, raw: Any, time: datetime
    ) -> dict[str, Any]:
        """Process data from `ethernet ports` endpoint"""

        # Ports info
        ports = {
            LAN: {},
            WAN: {},
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
        fw_new = parsers.firmware_string(raw["webs_state_info"]) or fw_current

        firmware[STATE] = fw_current < fw_new
        firmware["current"] = str(fw_current)
        firmware["available"] = str(fw_new)

        return {
            FIRMWARE: firmware,
        }

    def _process_monitor_light(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `light` endpoint"""

        # LED
        led = {}
        if LED_VAL in raw:
            led[STATE] = converters.bool_from_any(raw[LED_VAL])
            self._state_led = led[STATE]

        return {
            LED: led,
        }

    def _process_monitor_main(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `main` endpoint"""

        # CPU
        cpu = {}
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
        ram = {}
        # Data is in KiB. To get MB as they are shown in the device Web-GUI,
        # should be devided by 1024 (yes, those will be MiB)
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
        network = {}
        # Data in Bytes for traffic and bits/s for speeds
        if NETDEV in raw:
            # Calculate RX and TX from the HEX values.
            # If there is no current value, but there was one before, get it from storage.
            # Traffic resets only on device reboot or when above the limit.
            # Device disconnect / reconnect does NOT reset it
            network = parsers.network_usage(raw=raw[NETDEV])

            if self.monitor[MAIN].ready and NETWORK in self.monitor[MAIN]:
                # Calculate speeds
                time_delta = (time - self.monitor[MAIN].time).total_seconds()
                network = parsers.network_speed(
                    after=network,
                    before=self.monitor[MAIN][NETWORK],
                    time_delta=time_delta,
                )
        # Keep last data
        elif self.monitor[MAIN].ready and NETWORK in self.monitor[MAIN]:
            network = self.monitor[MAIN][NETWORK]

        if USB not in network and "dualwan" in self._identity.services:
            network[USB] = {}
        # Save constant
        constant = []
        for interface in network:
            if interface in WLAN_TYPE:
                constant.append(interface)
        self._init_constant(WLAN, constant)

        # WAN
        wan = {}
        if WANLINK_STATE in raw:
            # Populate WAN with known values
            wan = parsers.wan_state(raw=raw[WANLINK_STATE])
        # Keep last data
        elif self.monitor[MAIN].ready and WAN in self.monitor[MAIN]:
            wan = self.monitor[MAIN][WAN]

        return {
            CPU: cpu,
            NETWORK: network,
            RAM: ram,
            WAN: wan,
        }

    def _process_monitor_nvram(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `nvram` endpoint"""

        # Check whether data was received before trying to parse it
        if not raw:
            return {
                GWLAN: {},
                WLAN: {},
            }

        # WLAN
        wlan = {}
        dictionary = MAP_NVRAM.get(WLAN)
        if dictionary:
            for intf in self.constant[WLAN]:
                interface = WLAN_TYPE.get(intf)
                if interface is not None:
                    wlan[intf] = {}
                    for key in dictionary:
                        key_to_use = (key.value.format(interface))[4:]
                        wlan[intf][key_to_use] = key.method(
                            raw[key.value.format(interface)]
                        )

        # GWLAN
        gwlan = {}
        dictionary = MAP_NVRAM.get(GWLAN)
        if dictionary:
            for intf in self.constant[WLAN]:
                interface = WLAN_TYPE.get(intf)
                if interface is not None:
                    for gid in RANGE_GWLAN:
                        gwlan[f"{intf}_{gid}"] = {}
                        for key in dictionary:
                            key_to_use = (key.value.format(interface))[4:]
                            gwlan[f"{intf}_{gid}"][key_to_use] = key.method(
                                raw[key.value.format(f"{interface}.{gid}")]
                            )

        return {
            GWLAN: gwlan,
            WLAN: wlan,
        }

    def _process_monitor_onboarding(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `onboarding` endpoint"""

        # AiMesh nodes state
        aimesh = {}
        data = raw["get_cfg_clientlist"][0]
        for device in data:
            node = parsers.aimesh_node(device)
            aimesh[node.mac] = node

        # Client list
        clients = {}
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

    def _process_monitor_parental_control(
        self, raw: Any, time: datetime
    ) -> dict[str, Any]:
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
            as_is = {}
            for element in MAP_PARENTAL_CONTROL_ITEM:
                temp = raw[element.value].split(DELIMITER_PARENTAL_CONTROL_ITEM)
                as_is[element.get()] = []
                for temp_element in temp:
                    as_is[element.get()].append(element.method(temp_element))

            number = len(as_is[MAC])
            for i in range(0, number):
                rules[as_is[MAC][i]] = FilterDevice(
                    mac=as_is[MAC][i],
                    name=as_is[NAME][i],
                    type=MAP_PARENTAL_CONTROL_TYPE.get(as_is[TYPE][i], UNKNOWN),
                    timemap=as_is[TIMEMAP].get(i),
                )

        parental_control[RULES] = rules.copy()

        return {PARENTAL_CONTROL: parental_control}

    def _process_monitor_port_status(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `port status` endpoint"""

        # Ports info
        ports = {
            LAN: {},
            USB: {},
            WAN: {},
        }
        if f"{PORT}_{INFO}" in raw:
            data = raw[f"{PORT}_{INFO}"][self._identity.mac]
            for port in data:
                port_type = PORT_TYPES.get(port[0])
                port_id = converters.int_from_str(port[1:])
                # Replace needed key/value pairs
                for key in CONVERTERS[PORT_STATUS]:
                    if key.value in data[port]:
                        data[port][key.get()] = key.method(data[port][key.value])
                        if key.get() != key.value:
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
        clients_historic = {}
        if "nmpClient" in raw:
            data = raw["nmpClient"][0]
            for mac, description in data.items():
                if converters.is_mac_address(mac):
                    clients_historic[mac] = description

        clients = {}
        if "fromNetworkmapd" in raw:
            data = raw["fromNetworkmapd"][0]
            for mac, description in data.items():
                if converters.is_mac_address(mac):
                    clients[mac] = description

        return {
            CLIENTS: clients,
            CLIENTS_HISTORIC: clients_historic,
        }

    def _process_monitor_vpn(self, raw: Any, time: datetime) -> dict[str, Any]:
        """Process data from `vpn` endpoint"""

        # VPN
        vpn = raw

        return {
            VPN: vpn,
        }

    # <-- MONITORS

    # TECHNICAL -->

    async def _async_handle_error(self) -> None:
        """Actions to be taken on connection error"""

        # Drop history dependent monitor values
        for (monitor, data) in HD_DATA:
            if monitor in self.monitor and data in self.monitor[monitor]:
                self.monitor[monitor].pop(data)

        return

    def _init_constant(self, constant: str, value: Any) -> None:
        """Initialize constant"""

        _LOGGER.debug("Initializing constant `%s`=`%s`", constant, value)
        self.constant[constant] = value

    # <-- TECHNICAL

    async def async_handle_reboot(self) -> None:
        """Actions to be taken on reboot"""

        await self.async_keep_state_led()
        self._flag_reboot = False

        return

    # PROCESS DATA -->

    def _process_data_none(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Don't process the data"""

        return raw

    def _process_data_connected_devices(
        self, raw: dict[str, Any]
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

    # <-- PROCESS DATA

    # RETURN DATA -->

    async def async_get_data(
        self,
        data: str,
        monitor: str | list[str],
        merge: Merge = Merge.ANY,
        process: Callable[[str], dict[str, Any]] | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Return data from the first available monitor in the list"""

        result = {}

        # Convert to list if only one monitor is set
        monitor = [monitor] if isinstance(monitor, str) else monitor

        # Create a list of monitors
        monitors = []

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
        for _monitor in monitors:

            # Value is not cached or cache is disabled
            if (
                not await self.async_monitor_cached(_monitor, data)
                or use_cache is False
            ):
                await self.async_monitor(_monitor)

            # Receive data
            part = self.monitor[_monitor].get(data or {})

            # Update data
            compilers.update_rec(result, part)

        # Process data
        if process:
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

    async def async_get_connected_devices(
        self, use_cache: bool = True
    ) -> dict[str, ConnectedDevice]:
        """Return connected devices data"""

        return await self.async_get_data(
            data=CLIENTS,
            monitor=[self._endpoint_devices, ONBOARDING],
            merge=Merge.ALL,
            use_cache=use_cache,
            process=self._process_data_connected_devices,
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

        macs = [] if macs is None else converters.as_list(macs)
        rules = [] if rules is None else converters.as_list(rules)

        # Get current rules
        current_rules: dict = (await self.async_get_parental_control())[RULES]

        # Remove old rules for these MACs
        for mac in macs:
            if mac in current_rules:
                current_rules.pop(mac)
        for rule in rules:
            if rule.mac in current_rules:
                current_rules.pop(rule.mac)

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
        # Should include service name to run
        # and default mode to apply changes
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

        nvram = []
        for mode in AR_LEDG_MODE:
            nvram.append(AR_KEY_LEDG_RGB.format(mode))
        nvram.append(AR_KEY_LEDG_SCHEME)
        nvram.append(AR_KEY_LEDG_SCHEME_OLD)

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
        for num in range(1, self._ledg_count + 1):
            if num not in colors:
                if self._ledg_color and num in self._ledg_color:
                    colors[num] = self._ledg_color[num]
                else:
                    colors[num] = {}

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
