"""AsusRouter module.

This module contains the main class for interacting with an Asus device."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import aiohttp

from asusrouter.connection import Connection
from asusrouter.const import DEFAULT_CACHE_TIME, DEFAULT_TIMEOUT
from asusrouter.error import (
    AsusRouter404Error,
    AsusRouterAccessError,
    AsusRouterConnectionError,
    AsusRouterDataError,
)
from asusrouter.modules.attributes import AsusRouterAttribute
from asusrouter.modules.client import process_client
from asusrouter.modules.data import AsusData, AsusDataState
from asusrouter.modules.data_finder import (
    ASUSDATA_ENDPOINT_APPEND,
    ASUSDATA_MAP,
    AsusDataFinder,
    AsusDataMerge,
)
from asusrouter.modules.data_transform import transform_clients, transform_network
from asusrouter.modules.endpoint import Endpoint, EndpointControl, process, read
from asusrouter.modules.endpoint.error import AccessError
from asusrouter.modules.flags import Flag
from asusrouter.modules.identity import AsusDevice, collect_identity
from asusrouter.modules.parental_control import ParentalControlRule
from asusrouter.modules.port_forwarding import PortForwardingRule
from asusrouter.modules.service import async_call_service
from asusrouter.modules.state import (
    AsusState,
    get_datatype,
    keep_state,
    save_state,
    set_state,
)
from asusrouter.tools import legacy
from asusrouter.tools.converters import safe_list
from asusrouter.tools.readers import merge_dicts, readable_mac

_LOGGER = logging.getLogger(__name__)


class AsusRouter:
    """The interface class."""

    _cache_time: float = DEFAULT_CACHE_TIME
    _hostname: str

    _identity: Optional[AsusDevice] = None

    _state: dict[AsusData, AsusDataState] = {}

    _flags: Flag = Flag()

    def __init__(
        self,
        hostname: str,
        username: str,
        password: str,
        port: Optional[int] = None,
        use_ssl: bool = False,
        cache_time: Optional[float] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ):  # pylint: disable=too-many-arguments
        """Initialize the interface."""

        _LOGGER.debug("Initializing a new interface to `%s`", hostname)

        # Set the cache time
        if cache_time:
            self._cache_time = cache_time

        # Set the host
        self._hostname = hostname

        # Create a connection
        self._connection = Connection(
            hostname=hostname,
            username=username,
            password=password,
            port=port,
            use_ssl=use_ssl,
            session=session,
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
                self.async_run_service, led_state.data["state"], self._identity
            )

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

        # Return new identity
        return self._identity

    # ---------------------------
    # <-- Identity-related methods
    # ---------------------------

    # ---------------------------
    # Request-related methods -->
    # ---------------------------

    def _get_attribute(self, attribute: Optional[AsusRouterAttribute]) -> Optional[Any]:
        """Get an attribute value."""

        if not attribute:
            return None

        match (attribute):
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

        print("FLAGS: ", flags)

        if flags.get("reboot", False) is True:
            _LOGGER.debug("Reboot flag is set")
            await self._async_handle_reboot()

    async def async_api_query(
        self, endpoint: Endpoint | EndpointControl, payload: Optional[str] = None
    ):
        """A wrapper for the connection query method."""

        if endpoint in ASUSDATA_ENDPOINT_APPEND:
            payload = payload or ""
            for key, attribute in ASUSDATA_ENDPOINT_APPEND[endpoint].items():
                value = self._get_attribute(attribute)
                if value:
                    payload += f"{key}={value};"
            # Remove trailing semicolon
            payload = payload[:-1]

        _LOGGER.debug("Triggered method async_api_query: %s | %s", endpoint, payload)

        return await self._connection.async_query(endpoint, payload)

    async def async_api_load(
        self,
        endpoint: Endpoint | EndpointControl,
        request: str = "",
        retry: bool = False,
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
                # Reconnect
                await self.async_connect()
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
        endpoint: Endpoint | EndpointControl = EndpointControl.COMMAND,
    ):
        """Send a command to the device."""

        _LOGGER.debug("Triggered method async_api_command: %s | %s", endpoint, commands)

        return await self.async_api_load(
            endpoint=endpoint,
            request=str(commands),
        )

    # ---------------------------
    # <-- Request-related methods
    # ---------------------------

    def _where_to_get_data(self, datatype: AsusData) -> Optional[AsusDataFinder]:
        """Get the list of endpoints to get data from."""

        _LOGGER.debug("Triggered method _where_to_get_data")

        # Check that device identity is available
        if not self._identity:
            _LOGGER.debug("No device identity available")
            return None

        # Get the map
        data_map = ASUSDATA_MAP.get(datatype)
        if not data_map:
            return None

        # Check if endpoints are available
        for endpoint in data_map.endpoint:
            # Check endpoint availability in identity
            if self._identity.endpoints and self._identity.endpoints.get(endpoint) in (
                False,
                None,
            ):
                # Remove the endpoint from the map
                data_map.endpoint.remove(endpoint)

        _LOGGER.debug("Endpoints to check: %s", data_map.endpoint)

        return data_map

    def _transform_data(self, datatype: AsusData, data: Any) -> Any:
        """Transform data if needed."""

        _LOGGER.debug("Triggered method _transform_data for `%s`", datatype)

        if datatype == AsusData.CLIENTS:
            _LOGGER.debug("Transforming clients data")
            return transform_clients(data, self._state.get(AsusData.CLIENTS))

        if datatype == AsusData.NETWORK:
            _LOGGER.debug("Transforming network data")
            return transform_network(
                data,
                self._identity.services if self._identity else [],
                self._state.get(AsusData.NETWORK),
            )

        return data

    def _check_state(self, datatype: Optional[AsusData]) -> None:
        """Make sure the state object is available."""

        _LOGGER.debug("Triggered method _check_state")

        if not datatype:
            return

        # Add state object but make sure it's marked expired
        if datatype not in self._state:
            self._state[datatype] = AsusDataState(
                timestamp=(
                    datetime.now(timezone.utc) - timedelta(seconds=2 * self._cache_time)
                )
            )

    async def async_get_data(self, datatype: AsusData, force: bool = False) -> Any:
        """Generic method to get data from the device."""

        # Check if we have a state object for this data
        self._check_state(datatype)

        # If state object is active, wait for it to finish and return the data
        if self._state[datatype].active:
            try:
                _LOGGER.debug("Already in progress. Waiting for data to be fetched")
                await asyncio.wait_for(
                    self._state[datatype].inactive_event.wait(), DEFAULT_TIMEOUT
                )
            except asyncio.TimeoutError:
                _LOGGER.debug("Timeout while waiting for data. Will try fetching again")

        # Check if we have the data already and not forcing a refresh
        if self._state[datatype].data and not force:
            # Check if the data is younger than the cache time
            if datetime.now(timezone.utc) - self._state[datatype].timestamp < timedelta(
                seconds=self._cache_time
            ):
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

                # Fetch the data
                data = await self.async_api_load(endpoint, request)

                # Make sure, identity is available
                if not self._identity:
                    self._identity = await self.async_get_identity()

                result = merge_dicts(
                    result,
                    process(
                        endpoint,
                        data,
                        self._state,
                        self._identity.firmware,
                        self._identity.wlan,
                    ),
                )

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
            return self._state[datatype].data

        # Check flags
        await self._check_flags()

        # Return the data we were looking for
        _LOGGER.debug(
            "Returning data for `%s` with object type `%s`",
            datatype,
            type(self._state[datatype].data),
        )
        return self._state[datatype].data

    # ---------------------------
    # Service-related methods -->
    # ---------------------------

    async def async_run_service(
        self,
        service: str,
        arguments: Optional[dict[str, Any]] = None,
        apply: bool = False,
        expect_modify: bool = True,
        drop_connection: bool = False,
    ) -> bool:
        """Run a service."""

        _LOGGER.debug("Triggered method async_run_service")

        # Run the service
        result = await async_call_service(
            self.async_api_command,
            service,
            arguments,
            apply,
            expect_modify,
        )

        if drop_connection:
            await self._async_drop_connection()

        return result

    async def async_set_state(
        self,
        state: AsusState,
        arguments: Optional[dict[str, Any]] = None,
        expect_modify: bool = False,
    ) -> bool:
        """Set the state."""

        _LOGGER.debug("Triggered method async_set_state")

        _LOGGER.debug(
            "Setting state `%s` with arguments `%s`. Expecting modify: `%s`",
            state,
            arguments,
            expect_modify,
        )

        result = await set_state(
            self.async_run_service, state, arguments, expect_modify
        )

        if result is True:
            # Check if we have a state object for this data
            self._check_state(get_datatype(state))
            # Save the state
            save_state(state, self._state)

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

    async def async_apply_parental_control_rules(
        self,
        rules: dict[str, ParentalControlRule],
    ) -> bool:
        """Apply parental control rules."""

        request = legacy.compile_parental_control(rules)

        if request:
            return await self.async_run_service(
                service="restart_firewall",
                arguments=request,
                apply=True,
            )

        return False

    async def async_remove_parental_control_rules(
        self,
        macs: Optional[str | list[str]] = None,
        rules: Optional[ParentalControlRule | list[ParentalControlRule]] = None,
        apply: bool = True,
    ) -> dict[str, ParentalControlRule]:
        """Remove parental control rules"""

        _macs = set() if macs is None else set(safe_list(macs))
        rules = [] if rules is None else safe_list(rules)

        # Get current rules
        current_rules: dict = (await self.async_get_data(AsusData.PARENTAL_CONTROL))[
            "rules"
        ]

        # Remove old rules for these MACs
        for mac in _macs:
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
        rules: ParentalControlRule | list[ParentalControlRule],
    ) -> bool:
        """Set parental control rules"""

        rules = safe_list(rules)

        # Remove old rules for these MACs and get the rest of the list
        current_rules = await self.async_remove_parental_control_rules(
            rules, apply=False
        )

        # Add new rules
        for rule in rules:
            current_rules[rule.mac] = rule

        # Apply new rules
        return await self.async_apply_parental_control_rules(current_rules)

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
        current_rules = [rule for rule in current_rules if rule.ip_address not in ips]
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
    # General management -->
    # ---------------------------

    async def async_cleanup(self) -> None:
        """Cleanup the connection."""

        self._connection.reset_connection()

    # ---------------------------
    # <-- General management
    # ---------------------------
