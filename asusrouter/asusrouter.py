"""AsusRouter module.

This module contains the main class for interacting with an Asus device."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Optional

import aiohttp

from asusrouter.connection import Connection
from asusrouter.const import (
    DEFAULT_CACHE_TIME,
    DEFAULT_RESULT_SUCCESS,
    DEFAULT_TIMEOUT,
    RequestType,
)
from asusrouter.error import (
    AsusRouter404Error,
    AsusRouterAccessError,
    AsusRouterConnectionError,
    AsusRouterDataError,
)
from asusrouter.modules.attributes import AsusRouterAttribute
from asusrouter.modules.data import AsusData, AsusDataState
from asusrouter.modules.data_finder import (
    ASUSDATA_ENDPOINT_APPEND,
    ASUSDATA_MAP,
    ASUSDATA_NVRAM,
    AsusDataFinder,
    AsusDataMerge,
    add_conditional_data_alias,
    add_conditional_data_rule,
    remove_data_rule,
)
from asusrouter.modules.data_transform import (
    transform_clients,
    transform_cpu,
    transform_ethernet_ports,
    transform_network,
    transform_wan,
)
from asusrouter.modules.endpoint import (
    ENDPOINT_FORCE_REQUEST,
    Endpoint,
    EndpointControl,
    EndpointType,
    process,
    read,
)
from asusrouter.modules.endpoint.error import AccessError
from asusrouter.modules.firmware import Firmware
from asusrouter.modules.flags import Flag
from asusrouter.modules.identity import AsusDevice, collect_identity
from asusrouter.modules.port_forwarding import PortForwardingRule
from asusrouter.modules.service import async_call_service
from asusrouter.modules.state import (
    AsusState,
    add_conditional_state,
    get_datatype,
    keep_state,
    save_state,
    set_state,
)
from asusrouter.tools import legacy
from asusrouter.tools.converters import get_enum_key_by_value, safe_list
from asusrouter.tools.readers import merge_dicts

_LOGGER = logging.getLogger(__name__)


class AsusRouter:
    """The interface class."""

    def __init__(
        self,
        hostname: str,
        username: str,
        password: str,
        port: Optional[int] = None,
        use_ssl: bool = False,
        cache_time: Optional[float] = None,
        session: Optional[aiohttp.ClientSession] = None,
        dumpback: Optional[Callable[..., Awaitable[None]]] = None,
    ):  # pylint: disable=too-many-arguments
        """Initialize the interface."""

        _LOGGER.debug("Initializing a new interface to `%s`", hostname)

        # Set the cache time
        self._cache_time = cache_time or DEFAULT_CACHE_TIME

        # Set the host
        self._hostname: str = hostname

        # Set the device identity
        self._identity: Optional[AsusDevice] = None
        self._state: dict[AsusData, AsusDataState] = {}

        # Set the flags
        self._flags: Flag = Flag()
        # Time for change to take effect before available to fetch
        self._needed_time: Optional[int] = None
        # ID from the last called service
        self._last_id: Optional[int] = None

        # Create a connection
        self._connection = Connection(
            hostname=hostname,
            username=username,
            password=password,
            port=port,
            use_ssl=use_ssl,
            session=session,
            dumpback=dumpback,
        )

    # ---------------------------
    # Connection-related methods -->
    # ---------------------------

    async def async_connect(self) -> bool:
        """Connect to the device and get its identity."""

        _LOGGER.debug("Triggered method async_connect")

        # Connect to the device
        try:
            result = await self._connection.async_connect()
            if result is False:
                return False
        except Exception as ex:  # pylint: disable=broad-except
            raise ex

        # Get the device identity
        return await self.async_get_identity() is not None

    async def async_disconnect(self) -> bool:
        """Disconnect from the device."""

        _LOGGER.debug("Triggered method async_disconnect")

        # Disconnect from the device
        try:
            await self._connection.async_disconnect()
        except Exception as ex:  # pylint: disable=broad-except
            await self._async_handle_exception(ex)

        return True

    async def _async_drop_connection(self) -> None:
        """Drop the connection in case we know it cannot reply
        due to our last actions."""

        _LOGGER.debug("Triggered method _async_drop_connection")

        self._connection.reset_connection()

    async def _async_handle_exception(self, ex: Exception) -> None:
        """Handle exceptions."""

        _LOGGER.debug("Triggered method _async_handle_exception")

        raise ex

    async def _async_handle_reboot(self) -> None:
        """Handle reboot."""

        _LOGGER.debug("Triggered method _async_handle_reboot")

        led_state = self._state.get(AsusData.LED)
        if led_state and led_state.data:
            _LOGGER.debug("Restoring LED state")
            await keep_state(
                callback=self.async_run_service,
                states=led_state.data["state"],
                identity=self._identity,
            )

        # Reset the reboot flag
        self._reset_flag("reboot")

    def _reset_flag(self, flag: str) -> None:
        """Reset a flag."""

        _LOGGER.debug("Triggered method _reset_flag")

        # Check that AsusData.FLAGS is available
        if AsusData.FLAGS not in self._state:
            return

        # Get the data from the state
        data = self._state[AsusData.FLAGS].data

        # Check that data is a dict
        if not isinstance(data, dict):
            return

        # Reset the flag
        data.pop(flag, None)

        _LOGGER.debug("Flag `%s` reset", flag)

    # ---------------------------
    # <-- Connection-related methods
    # ---------------------------

    # ---------------------------
    # Identity-related methods -->
    # ---------------------------

    async def async_get_identity(self, force: bool = False) -> AsusDevice:
        """Get the device identity."""

        _LOGGER.debug("Triggered method async_get_identity")

        # Check whether we already have the identity and not forcing a refresh
        if self._identity and not force:
            return self._identity

        # Collect the identity
        self._identity = await collect_identity(
            api_hook=self.async_api_hook,
            api_query=self.async_api_query,
        )

        # Add conditional data rules
        if self._identity:
            firmware = self._identity.firmware
            merlin = self._identity.merlin
            fw_388 = Firmware(major="3.0.0.4", minor=388, build=0)
            # Stock
            if not merlin:
                _LOGGER.debug("Adding conditional rules for stock firmware")
                if fw_388 < firmware:
                    add_conditional_state(
                        AsusState.OPENVPN_CLIENT, AsusData.VPNC
                    )
                    add_conditional_state(
                        AsusState.WIREGUARD_CLIENT, AsusData.VPNC
                    )
                    add_conditional_data_alias(
                        AsusData.OPENVPN_CLIENT, AsusData.VPNC
                    )
                    add_conditional_data_alias(
                        AsusData.WIREGUARD_CLIENT, AsusData.VPNC
                    )
                    add_conditional_data_rule(
                        AsusData.OPENVPN_SERVER,
                        AsusDataFinder(
                            Endpoint.HOOK,
                            nvram=ASUSDATA_NVRAM["openvpn_server_388"],
                        ),
                    )
            # Merlin
            else:
                _LOGGER.debug("Adding conditional rules for Merlin firmware")
                if fw_388 < firmware:
                    add_conditional_data_rule(
                        AsusData.VPNC,
                        AsusDataFinder(
                            Endpoint.HOOK,
                            nvram=ASUSDATA_NVRAM["vpnc"],
                        ),
                    )
            # Before 388
            if firmware < fw_388:
                # Remove VPNC rules
                remove_data_rule(AsusData.VPNC)
                remove_data_rule(AsusData.VPNC_CLIENTLIST)
                # Remove WireGuard rules
                remove_data_rule(AsusData.WIREGUARD)
                remove_data_rule(AsusData.WIREGUARD_CLIENT)
                remove_data_rule(AsusData.WIREGUARD_SERVER)

            # Ookla Speedtest
            if self._identity.ookla is False:
                remove_data_rule(AsusData.SPEEDTEST)
                # remove_data_rule(AsusData.SPEEDTEST_HISTORY)
                remove_data_rule(AsusData.SPEEDTEST_RESULT)
                # remove_data_rule(AsusData.SPEEDTEST_SERVERS)

        # Return new identity
        return self._identity

    # ---------------------------
    # <-- Identity-related methods
    # ---------------------------

    # ---------------------------
    # Request-related methods -->
    # ---------------------------

    def _get_attribute(
        self, attribute: Optional[AsusRouterAttribute]
    ) -> Optional[Any]:
        """Get an attribute value."""

        if not attribute:
            return None

        match attribute:
            case AsusRouterAttribute.MAC:
                if self._identity:
                    return self._identity.mac
            case AsusRouterAttribute.WLAN_LIST:
                if self._identity:
                    return self._identity.wlan

        return None

    async def _check_flags(self) -> None:
        """Check flags."""

        _LOGGER.debug("Triggered method _check_flags")

        flags: dict[str, bool] = {}

        state_flags = self._state.get(AsusData.FLAGS)
        if isinstance(state_flags, AsusDataState) and isinstance(
            state_flags.data, dict
        ):
            flags = state_flags.data

        if flags.get("reboot", False) is True:
            _LOGGER.debug("Reboot flag is set")
            await self._async_handle_reboot()

    async def async_api_query(
        self, endpoint: EndpointType, payload: Optional[str] = None
    ):
        """A wrapper for the connection query method."""

        if endpoint in ASUSDATA_ENDPOINT_APPEND:
            payload = payload or ""
            for key, attribute in ASUSDATA_ENDPOINT_APPEND[endpoint].items():
                if isinstance(attribute, AsusRouterAttribute):
                    value = self._get_attribute(attribute)
                else:
                    value = attribute
                if value:
                    payload += f"{key}={value};"
            # Remove trailing semicolon
            payload = payload[:-1]

        _LOGGER.debug(
            "Triggered method async_api_query: %s | %s", endpoint, payload
        )

        request_type = ENDPOINT_FORCE_REQUEST.get(endpoint, RequestType.POST)

        return await self._connection.async_query(
            endpoint, payload, request_type=request_type
        )

    async def async_api_load(
        self,
        endpoint: EndpointType,
        request: str = "",
        retry: int = 0,
    ) -> dict[str, Any]:
        """Load API endpoint with optional request."""

        _LOGGER.debug("Triggered method async_api_load: %s", endpoint)

        # Load the endpoint
        try:
            status, _, content = await self.async_api_query(endpoint, request)
        except AsusRouter404Error:
            _LOGGER.debug("Endpoint %s not found", endpoint)
            return {}
        except AsusRouterAccessError as ex:
            # Check whether we are not connected
            args = ex.args
            if args[1] == AccessError.AUTHORIZATION:
                # Mark the connection as dropped
                await self._async_drop_connection()
                # Wait before repeating the request
                await asyncio.sleep(1 + retry * 3)
                # Repeat request once more and see what happens
                return await self.async_api_load(endpoint, request, True)
            # Otherwise just raise the exception
            raise ex

        # Log status
        _LOGGER.debug("Response %s received from %s", status, endpoint)

        # Try to read the content
        try:
            result = read(endpoint, content)
        except json.JSONDecodeError as ex:
            # Not like this is supposed to happen, but just in case
            _LOGGER.debug("Failed to read content from %s", endpoint)
            _LOGGER.debug("Content: %s", content)
            # Just repeat request once more and see what happens
            # Only if we haven't tried already
            if not retry:
                return await self.async_api_load(endpoint, request, True)
            raise AsusRouterDataError(
                "Something went wrong while reading the content"
            ) from ex

        # Check if we need to drop the connection
        run_service = result.get("run_service", None)
        if run_service in ("restart_httpd", "reboot"):
            await self._async_drop_connection()

        return result

    async def async_api_hook(self, request: str) -> dict[str, Any]:
        """Hook to the device API. Hooks are used to fetch data from the device."""

        _LOGGER.debug("Triggered method async_api_hook: %s", request)

        return await self.async_api_load(
            endpoint=Endpoint.HOOK,
            request=f"hook={request}",
        )

    async def async_api_command(
        self,
        commands: Optional[dict[str, str]],
        endpoint: EndpointType = EndpointControl.COMMAND,
    ):
        """Send a command to the device."""

        _LOGGER.debug(
            "Triggered method async_api_command: %s | %s", endpoint, commands
        )

        return await self.async_api_load(
            endpoint=endpoint,
            request=str(commands),
        )

    # ---------------------------
    # <-- Request-related methods
    # ---------------------------

    def _where_to_get_data(
        self, datatype: AsusData
    ) -> Optional[AsusDataFinder]:
        """Get the list of endpoints to get data from."""

        _LOGGER.debug("Triggered method _where_to_get_data")

        # Check that device identity is available
        if not self._identity:
            _LOGGER.debug("No device identity available")
            return None

        # Get the map
        data_map = ASUSDATA_MAP.get(datatype)
        # Consider aliases
        while isinstance(data_map, AsusData):
            data_map = ASUSDATA_MAP.get(data_map)
        # Check if we have a map
        if not isinstance(data_map, AsusDataFinder):
            _LOGGER.debug("No map found for %s", datatype)
            return None

        # Check if endpoints are available
        for endpoint in data_map.endpoint:
            # Check endpoint availability in identity
            if self._identity.endpoints and self._identity.endpoints.get(
                endpoint
            ) in (
                False,
                None,
            ):
                # Remove the endpoint from the map
                data_map.endpoint.remove(endpoint)

        _LOGGER.debug("Endpoints to check: %s", data_map.endpoint)

        return data_map

    def _transform_data(
        self, datatype: AsusData, data: Any, **kwargs: Any
    ) -> Any:
        """Transform data if needed."""

        _LOGGER.debug("Triggered method _transform_data for `%s`", datatype)

        if datatype == AsusData.CLIENTS:
            _LOGGER.debug("Transforming clients data")
            return transform_clients(
                data,
                self._state.get(AsusData.CLIENTS),
                aimesh=self._identity.aimesh if self._identity else False,
            )

        if datatype == AsusData.CPU:
            _LOGGER.debug("Transforming CPU data")
            return transform_cpu(data)

        if datatype == AsusData.NETWORK:
            _LOGGER.debug("Transforming network data")
            return transform_network(
                data,
                self._identity.services if self._identity else [],
                self._state.get(AsusData.NETWORK),
                model=self._identity.model if self._identity else None,
            )

        if datatype == AsusData.PORTS:
            _LOGGER.debug("Transforming port data")
            return transform_ethernet_ports(
                data,
                self._identity.mac if self._identity else None,
            )

        if datatype == AsusData.WAN:
            _LOGGER.debug("Transforming WAN data")
            return transform_wan(
                data,
                self._identity.services if self._identity else [],
            )

        return data

    def _drop_data(self, datatype: AsusData, endpoint: EndpointType) -> bool:
        """Check whether data should be dropped. This is required
        for some data obtained from multiple endpoints."""

        if not self._identity:
            return False

        if datatype == AsusData.OPENVPN_CLIENT:
            if self._identity.merlin is True:
                return endpoint == Endpoint.HOOK

        return False

    async def _check_prerequisites(self, datatype: AsusData) -> None:
        """Check prerequisites before fetching data."""

        _LOGGER.debug(
            "Triggered method _check_prerequisites for datatype `%s`", datatype
        )

        # A placeholder for future checks
        return

    async def _check_postrequisites(self, datatype: AsusData) -> None:
        """Check postrequisites after fetching data.

        This method is also used to fetch additional data."""

        _LOGGER.debug(
            "Triggered method _check_postrequisites for datatype `%s`",
            datatype,
        )

        # Firmware
        if datatype == AsusData.FIRMWARE:
            # Check if update is available
            firmware = self._state[AsusData.FIRMWARE].data
            if firmware and firmware["state"] is True:
                # Get release notes
                release_note = await self.async_get_data(
                    AsusData.FIRMWARE_NOTE, force=True
                )
                if release_note:
                    firmware.update(release_note)
        return

    def _check_state(self, datatype: Optional[AsusData]) -> None:
        """Make sure the state object is available."""

        _LOGGER.debug("Triggered method _check_state")

        if not datatype:
            return

        # Add state object but make sure it's marked expired
        if datatype not in self._state:
            self._state[datatype] = AsusDataState(
                timestamp=(
                    datetime.now(timezone.utc)
                    - timedelta(seconds=2 * self._cache_time)
                )
            )

    def _return_state(self, datatype: AsusData, **kwargs: Any) -> Any:
        """Return a proper state."""

        _LOGGER.debug("Triggered method _return_state")

        # Get the state
        state = self._state[datatype].data

        if datatype == AsusData.PORTS:
            own_mac = self._identity.mac if self._identity else None

            # Get the device selected
            device = kwargs.get("device", None)

            match device:
                case None:
                    if isinstance(state, dict):
                        return state.get(own_mac, {})
                    return state
                case "all":
                    return state
                # Case when substate is a MAC address
                case a if isinstance(a, str):
                    if isinstance(state, dict) and a in state:
                        return state[a]
                    return {}

        return state

    async def async_get_data(
        self, datatype: AsusData, force: bool = False, **kwargs: Any
    ) -> Any:
        """Generic method to get data from the device."""

        # Check if we have a state object for this data
        self._check_state(datatype)

        # If state object is active, wait for it to finish and return the data
        if self._state[datatype].active:
            try:
                _LOGGER.debug(
                    "Already in progress. Waiting for data to be fetched"
                )
                await asyncio.wait_for(
                    self._state[datatype].inactive_event.wait(),
                    DEFAULT_TIMEOUT,
                )
            except asyncio.TimeoutError:
                _LOGGER.debug(
                    "Timeout while waiting for data. Will try fetching again"
                )

        # Check if we have the data already and not forcing a refresh
        if self._state[datatype].data and not force:
            # Check if the data is younger than the cache time
            if datetime.now(timezone.utc) - self._state[
                datatype
            ].timestamp < timedelta(seconds=self._cache_time):
                _LOGGER.debug(
                    "Using cached data for `%s`: %s",
                    datatype,
                    self._state[datatype].data,
                )
                # Return the cached data
                return self._state[datatype].data
            _LOGGER.debug("Data for %s is too old. Fetching", datatype)

        # Mark the data as active
        self._state[datatype].start()

        # Check prerequisites
        await self._check_prerequisites(datatype)

        # Get the data finder
        data_finder = self._where_to_get_data(datatype)

        # Check if we have a data finder
        if not data_finder:
            _LOGGER.debug("No data finder for %s", datatype)
            return {}

        # The data we are looking for
        data = {}
        result: dict[AsusData, Any] = {}

        try:
            for endpoint in data_finder.endpoint:
                # Get the data from the endpoint
                request = "hook=" if endpoint == Endpoint.HOOK else ""
                for item in data_finder.request:
                    key, value = item
                    request += f"{key}({value});"
                if data_finder.method:
                    argument = self._get_attribute(data_finder.arguments)
                    request += (
                        data_finder.method(argument)
                        if argument
                        else data_finder.method()
                    )
                # Check that we are not fetching this data already

                # Add the request from kwargs
                kw_request = kwargs.get("request", {})
                if isinstance(kw_request, dict):
                    for key, value in kw_request.items():
                        request += f"{key}={value};"
                    # Remove trailing symbol
                    request = request[:-1]

                # Fetch the data
                data = await self.async_api_load(endpoint, request)

                # Make sure, identity is available
                if not self._identity:
                    self._identity = await self.async_get_identity()

                processed = process(
                    endpoint,
                    data,
                    self._state,
                    self._identity.firmware,
                    self._identity.wlan,
                )

                # Check whether data should be dropped
                to_drop = []
                for key, value in processed.items():
                    if self._drop_data(key, endpoint):
                        to_drop.append(key)
                for key in to_drop:
                    processed.pop(key, None)

                result = merge_dicts(result, processed)

                # Check if we have data and data finder merge is ANY
                if result and data_finder.merge == AsusDataMerge.ANY:
                    break

            # Save the data state
            for key, value in result.items():
                # Transform data if needed
                value = self._transform_data(key, value)
                # Save the data
                result[key] = value
                # Update the state
                if key not in self._state:
                    self._state[key] = AsusDataState()
                self._state[key].update(value)
        except (AsusRouterConnectionError, AsusRouterDataError):
            return self._return_state(datatype, **kwargs)

        # Check flags
        await self._check_flags()

        # Check postrequisites
        await self._check_postrequisites(datatype)

        # Return the data we were looking for
        _LOGGER.debug(
            "Returning data for `%s` with object type `%s`",
            datatype,
            type(self._state[datatype].data),
        )
        return self._return_state(datatype, **kwargs)

    # ---------------------------
    # Service-related methods -->
    # ---------------------------

    async def async_run_service(
        self,
        service: Optional[str],
        arguments: Optional[dict[str, Any]] = None,
        apply: bool = False,
        expect_modify: bool = True,
        drop_connection: bool = False,
    ) -> bool:
        """Run a service."""

        _LOGGER.debug("Triggered method async_run_service")

        # Run the service
        result, self._needed_time, self._last_id = await async_call_service(
            self.async_api_command,
            service,
            arguments,
            apply,
            expect_modify,
        )

        if drop_connection:
            await self._async_drop_connection()

        return result

    async def _async_check_state_dependency(self, state: AsusState) -> None:
        """Check and queue state dependencies. Required for some states."""

        _LOGGER.debug("Triggered method _async_check_state_dependency")

        dependency = get_datatype(state)

        if dependency == AsusData.VPNC:
            # VPNC state change requires the correct previous state
            await self.async_get_data(AsusData.VPNC, force=True)

        if dependency == AsusData.AURA:
            # Aura state change requires the correct previous state
            await self.async_get_data(AsusData.AURA, force=True)

        return

    async def _async_get_state_callback(
        self, state: AsusState
    ) -> Callable[..., Awaitable]:
        """Get the state callback."""

        _LOGGER.debug("Triggered method _async_get_state_callback")

        datatype = get_datatype(state)
        # If state is one of AsusState.AURA enum
        if datatype == AsusData.AURA:
            return self.async_api_command

        return self.async_run_service

    async def async_set_state(
        self,
        state: AsusState,
        expect_modify: bool = False,
        **kwargs: Any,
    ) -> bool:
        """Set the state."""

        _LOGGER.debug("Triggered method async_set_state")

        _LOGGER.debug(
            "Setting state `%s` with arguments `%s`. Expecting modify: `%s`",
            state,
            kwargs,
            expect_modify,
        )

        # Check dependencies
        await self._async_check_state_dependency(state)

        # Get the state callback
        callback = await self._async_get_state_callback(state)

        result = await set_state(
            callback=callback,
            state=state,
            expect_modify=expect_modify,
            router_state=self._state,
            identity=self._identity,
            **kwargs,
        )

        # Rewrite the result if it is the default one
        if result == DEFAULT_RESULT_SUCCESS:
            result = True

        if result is True:
            _datatype = get_datatype(state)

            if _datatype in (AsusData.VPNC, AsusData.AURA):
                # The only way to make it work with VPN Fusion
                await asyncio.sleep(1)
                await self._async_check_state_dependency(state)
            elif (
                get_enum_key_by_value(
                    AsusState, type(state), default=AsusState.NONE
                )
                == AsusState.PC_RULE
            ):
                # We should not save this state, since it is saved differently
                pass
            else:
                # Check if we have a state object for this data
                self._check_state(_datatype)
                # Save the state
                _LOGGER.debug(
                    "Saving state `%s` for `%s` s with id=`%s`",
                    state,
                    self._needed_time,
                    self._last_id,
                )
                save_state(
                    state, self._state, self._needed_time, self._last_id
                )
                # Reset the needed time and last id
                self._needed_time = None
                self._last_id = None

        return result

    # ---------------------------
    # <-- Service-related methods
    # ---------------------------

    # ---------------------------
    # Legacy methods -->
    # ---------------------------
    # Not tested, not used, not documented
    # This part can be changed / removed in the future
    # It might also not be working properly

    async def async_apply_port_forwarding_rules(
        self,
        rules: list[PortForwardingRule],
    ) -> bool:
        """Apply port forwarding rules"""

        request = legacy.compile_port_forwarding(rules)

        if request:
            return await self.async_run_service(
                service="restart_firewall",
                arguments=request,
                apply=True,
            )

        return False

    async def async_remove_port_forwarding_rules(
        self,
        ips: str | list[str] | None = None,
        rules: PortForwardingRule | list[PortForwardingRule] | None = None,
        apply: bool = True,
    ) -> list[PortForwardingRule]:
        """Remove port forwarding rules"""

        ips = set() if ips is None else set(safe_list(ips))
        rules = [] if rules is None else safe_list(rules)

        # Get current rules
        current_rules: list[PortForwardingRule] = (
            await self.async_get_data(AsusData.PORT_FORWARDING)
        )["rules"]

        # Remove all rules for these IPs
        current_rules = [
            rule for rule in current_rules if rule.ip_address not in ips
        ]
        # Remove exact rules
        for rule_to_find in rules:
            current_rules = [
                rule
                for rule in current_rules
                if not (
                    rule.ip_address == rule_to_find.ip_address
                    and rule.port_external == rule_to_find.port_external
                    and rule.protocol == rule_to_find.protocol
                    and (
                        rule_to_find.ip_external is None
                        or rule.ip_external == rule_to_find.ip_external
                    )
                    and (
                        rule_to_find.port is None
                        or rule.port == rule_to_find.port
                    )
                )
            ]

        # Apply new rules
        if apply:
            await self.async_apply_port_forwarding_rules(current_rules)

        # Return the new rules
        return current_rules

    async def async_set_port_forwarding_rules(
        self,
        rules: PortForwardingRule | list[PortForwardingRule],
    ) -> bool:
        """Set port forwarding rules"""

        rules = safe_list(rules)

        # Get current rules
        current_rules: list[PortForwardingRule] = (
            await self.async_get_data(AsusData.PORT_FORWARDING)
        )["rules"]

        # Add new rules
        for rule in rules:
            current_rules.append(rule)

        # Apply new rules
        return await self.async_apply_port_forwarding_rules(current_rules)

    # ---------------------------
    # <-- Legacy methods
    # ---------------------------

    # ---------------------------
    # Properties -->
    # ---------------------------

    @property
    def connected(self) -> bool:
        """Return connection status."""

        return self._connection.connected

    # ---------------------------
    # <-- Properties
    # ---------------------------

    # ---------------------------
    # Additional settings -->
    # ---------------------------

    # ---------------------------
    # <-- Additional settings
    # ---------------------------

    # ---------------------------
    # General management -->
    # ---------------------------

    async def async_cleanup(self) -> None:
        """Cleanup the connection."""

        self._connection.reset_connection()

    # ---------------------------
    # <-- General management
    # ---------------------------
