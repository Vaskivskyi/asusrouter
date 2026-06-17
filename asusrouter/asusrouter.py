"""AsusRouter module.

This module contains the main class for interacting with an Asus device.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable
from datetime import UTC, datetime, timedelta
import json
import logging
from typing import Any

import aiohttp

from asusrouter.config import ARConfigKey as ARConfKey, ARInstanceConfig
from asusrouter.connection import Connection
from asusrouter.connection_config import ARConnectionConfigKey as ARCCKey
from asusrouter.const import (
    AR_CALL_GET_STATE,
    AR_CALL_TRANSLATE_STATE,
    DEFAULT_CACHE_TIME,
    DEFAULT_PORT_HTTP,
    DEFAULT_PORT_HTTPS,
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
from asusrouter.modules.device import ARDeviceSourceUniversal
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import (
    ENDPOINT_FORCE_REQUEST,
    Endpoint,
    EndpointControl,
    EndpointType,
    process,
    read,
)
from asusrouter.modules.endpoint.error import AccessError
from asusrouter.modules.firmware import ARFirmware, ARFirmwareType
from asusrouter.modules.flags import Flag
from asusrouter.modules.port_forwarding import PortForwardingRule
from asusrouter.modules.service import async_call_service
from asusrouter.modules.source import (
    ARDataCollection,
    ARDataSource,
    ARDataState,
    ARDataStateDynamic,
    ARDataStateStatic,
    ARDataType,
)
from asusrouter.modules.state import (
    AsusState,
    add_conditional_state,
    get_datatype,
    keep_state,
    save_state,
    set_state,
)
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.modules.support.helpers import support_available
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools import legacy
from asusrouter.tools.converters import get_enum_key_by_value, safe_list
from asusrouter.tools.readers import merge_dicts
from asusrouter.tools.types import ARCallableType, ARCallbackType

_LOGGER = logging.getLogger(__name__)

ARDataRequest = ARDataSource | ARDataType | Iterable[ARDataSource | ARDataType]

_FW_388 = ARFirmware(major=(3, 0, 0, 4), minor=388)


class AsusRouter:
    """The interface class."""

    def __init__(  # noqa: PLR0913
        self,
        hostname: str,
        username: str,
        password: str,
        port: int | None = None,
        use_ssl: bool = False,
        cache_time: float | None = None,
        session: aiohttp.ClientSession | None = None,
        dumpback: Callable[..., Awaitable[None]] | None = None,
        config: dict[ARConfKey, Any] | None = None,
        connection_config: dict[ARCCKey, Any] | None = None,
    ):
        """Initialize the interface."""

        _LOGGER.debug("Initializing a new interface to `%s`", hostname)

        # Initialize configs
        _LOGGER.debug("Setting up AR instance config: %s", config)
        self._config = ARInstanceConfig(defaults=config)

        # Set the cache time
        self._cache_time = cache_time or DEFAULT_CACHE_TIME
        self._cache_threshold = timedelta(seconds=self._cache_time)

        # Set the host
        self._hostname: str = hostname

        self._state: dict[AsusData, AsusDataState] = {}
        self._data_states: dict[ARDataSource | ARDataType, ARDataState] = {}

        # Set the flags
        self._flags: Flag = Flag()
        # Time for change to take effect before available to fetch
        self._needed_time: int | None = None
        # ID from the last called service
        self._last_id: int | None = None

        # Create an empty connection and save the credentials
        self._connection: Connection | None = None
        self._username = username
        self._password = password
        self._port = port
        self._use_ssl = use_ssl
        self._session = session
        self._dumpback = dumpback
        self._connection_config = connection_config

    # ---------------------------
    # Connection-related methods -->
    # ---------------------------

    async def async_init_connection(self) -> None:
        """Initialize the connection."""

        _LOGGER.debug("Triggered method async_init_connection")

        self._connection = await Connection.create(
            hostname=self._hostname,
            username=self._username,
            password=self._password,
            port=self._port,
            use_ssl=self._use_ssl,
            session=self._session,
            timeout=DEFAULT_TIMEOUT,
            dumpback=self._dumpback,
            config=self._connection_config,
        )

    async def async_del_connection(self) -> None:
        """Delete the connection."""

        _LOGGER.debug("Triggered method async_del_connection")

        # Disconnect from the device if connected
        await self.async_disconnect()

        # Close the connection
        if self._connection:
            await self._connection.async_close()
            self._connection = None

    async def async_connect(self) -> bool:
        """Connect to the device and get its identity."""

        _LOGGER.debug("Triggered method async_connect")

        # Make sure the connection is initialized
        if self._connection is None:
            await self.async_init_connection()

        # Connect to the device
        result = await self._connection.async_connect()
        if result is False:
            return False

        # Fetch the device description
        result = await self.async_get_data_v2(
            ARDeviceSourceUniversal, force=True
        )
        # Apply legacy conditional data rules
        await self.async_get_identity()

        return result is not None

    async def async_disconnect(self) -> bool:
        """Disconnect from the device."""

        _LOGGER.debug("Triggered method async_disconnect")

        # Disconnect from the device
        try:
            if self._connection:
                await self._connection.async_disconnect()
        except Exception as ex:  # noqa: BLE001
            self._async_handle_exception(ex)

        return True

    def _async_drop_connection(self) -> None:
        """Drop the connection.

        In case we know it cannot reply due to our last actions.
        """

        _LOGGER.debug("Triggered method _async_drop_connection")

        if self._connection:
            self._connection.reset_connection()

    def _async_handle_exception(self, ex: Exception) -> None:
        """Handle exceptions."""

        _LOGGER.debug("Triggered method _async_handle_exception")

        raise ex

    async def _async_handle_reboot(self) -> None:
        """Handle reboot."""

        _LOGGER.debug("Triggered method _async_handle_reboot")

        led_state = self._state.get(AsusData.LED)
        if led_state and led_state.data:
            led_data = led_state.data
            _LOGGER.debug("Restoring LED state")
            await keep_state(
                callback=self.async_run_service,
                states=led_data["state"],
                identity=self.description,
            )

        # Reset the reboot flag
        self._reset_flag("reboot")

    def _reset_flag(self, flag: str) -> None:
        """Reset a flag."""

        _LOGGER.debug("Triggered method _reset_flag")

        # Check that AsusData.FLAGS is available with dict data
        flags_state = self._state.get(AsusData.FLAGS)
        if flags_state is None:
            return

        data = flags_state.data
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

    async def async_get_identity(self) -> None:
        """Apply conditional data rules based on device description."""

        _LOGGER.debug("Triggered method async_get_identity")

        # Add conditional data rules
        firmware = self.description.firmware
        merlin = firmware.firmware_type in (
            ARFirmwareType.MERLIN,
            ARFirmwareType.GNUTON,
        )
        support = self.support
        # Stock
        if not merlin:
            _LOGGER.debug("Adding conditional rules for stock firmware")
            if firmware > _FW_388:
                add_conditional_state(AsusState.OPENVPN_CLIENT, AsusData.VPNC)
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
        # Merlin / Gnuton
        else:
            _LOGGER.debug("Adding conditional rules for Merlin firmware")
            if firmware > _FW_388:
                add_conditional_data_rule(
                    AsusData.VPNC,
                    AsusDataFinder(
                        Endpoint.HOOK,
                        nvram=ASUSDATA_NVRAM["vpnc"],
                    ),
                )
        # Before 388
        if firmware < _FW_388:
            # Remove VPNC rules
            remove_data_rule(AsusData.VPNC)
            remove_data_rule(AsusData.VPNC_CLIENTLIST)
            # Remove WireGuard rules
            remove_data_rule(AsusData.WIREGUARD)
            remove_data_rule(AsusData.WIREGUARD_CLIENT)
            remove_data_rule(AsusData.WIREGUARD_SERVER)

        # DSL connection
        if not support_available(support, ARSupportType.DSL):
            remove_data_rule(AsusData.DSL)

        # Ookla Speedtest
        if not support_available(support, ARSupportType.SPEEDTEST):
            remove_data_rule(AsusData.SPEEDTEST)
            # remove_data_rule(AsusData.SPEEDTEST_HISTORY)
            remove_data_rule(AsusData.SPEEDTEST_RESULT)
            # remove_data_rule(AsusData.SPEEDTEST_SERVERS)

    # ---------------------------
    # <-- Identity-related methods
    # ---------------------------

    # ---------------------------
    # Request-related methods -->
    # ---------------------------

    def _get_attribute(
        self, attribute: AsusRouterAttribute | None
    ) -> Any | None:
        """Get an attribute value."""

        if attribute is None:
            return None

        match attribute:
            case AsusRouterAttribute.MAC:
                mac = self.description.mac
                return str(mac) if mac else None
            case AsusRouterAttribute.WLAN_LIST:  # TODO: Identity migration
                return self.description

        return None

    async def _check_flags(self) -> None:
        """Check flags."""

        _LOGGER.debug("Triggered method _check_flags")

        state_flags = self._state.get(AsusData.FLAGS)
        _data = (
            state_flags.data
            if isinstance(state_flags, AsusDataState)
            else None
        )
        flags = _data if isinstance(_data, dict) else {}

        if flags.get("reboot") is True:
            _LOGGER.debug("Reboot flag is set")
            await self._async_handle_reboot()

    async def async_api_query(
        self, endpoint: EndpointType, payload: str | None = None
    ) -> tuple[int, dict[str, str], str]:
        """Query the API endpoint."""

        if endpoint in ASUSDATA_ENDPOINT_APPEND:
            payload = payload or ""
            appended = False
            for key, attribute in ASUSDATA_ENDPOINT_APPEND[endpoint].items():
                if isinstance(attribute, AsusRouterAttribute):
                    value = self._get_attribute(attribute)
                else:
                    value = attribute
                if value:
                    payload += f"{key}={value};"
                    appended = True
            if appended:
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
            if ex.args[1] == AccessError.AUTHORIZATION:
                # Mark the connection as dropped
                self._async_drop_connection()
                # Wait before repeating the request
                await asyncio.sleep(1 + retry * 3)
                # Repeat request once more and see what happens
                return await self.async_api_load(endpoint, request, 1)
            # Otherwise just raise the exception
            raise

        # Log status
        _LOGGER.debug("Response %s received from %s", status, endpoint)

        # Try to read the content
        try:
            result = read(endpoint, content, config=self.config)
        except json.JSONDecodeError as ex:
            # Not like this is supposed to happen, but just in case
            _LOGGER.debug(
                "Failed to read content from %s: %s", endpoint, content
            )
            # Just repeat request once more and see what happens
            # Only if we haven't tried already
            if not retry:
                return await self.async_api_load(endpoint, request, 1)
            raise AsusRouterDataError(
                "Something went wrong while reading the content"
            ) from ex

        # Check if we need to drop the connection
        run_service = result.get("run_service")
        if run_service in ("restart_httpd", "reboot"):
            self._async_drop_connection()

        return result

    async def async_api_hook(self, request: str) -> dict[str, Any]:
        """Perform a hook to the device API.

        Hooks are used to fetch data from the device.
        """

        _LOGGER.debug("Triggered method async_api_hook: %s", request)

        return await self.async_api_load(
            endpoint=Endpoint.HOOK,
            request=f"hook={request}",
        )

    async def async_api_command(
        self,
        commands: dict[str, str] | None,
        endpoint: EndpointType = EndpointControl.COMMAND,
    ) -> dict[str, Any]:
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

    def _where_to_get_data(self, datatype: AsusData) -> AsusDataFinder | None:
        """Get the list of endpoints to get data from."""

        _LOGGER.debug("Triggered method _where_to_get_data")

        # Get the map
        data_map = ASUSDATA_MAP.get(datatype)
        # Consider aliases
        while isinstance(data_map, AsusData):
            data_map = ASUSDATA_MAP.get(data_map)
        # Check if we have a map
        if not isinstance(data_map, AsusDataFinder):
            _LOGGER.debug("No map found for %s", datatype)
            return None

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
                aimesh=support_available(self.support, ARSupportType.AIMESH),
            )

        if datatype == AsusData.CPU:
            _LOGGER.debug("Transforming CPU data")
            return transform_cpu(data)

        if datatype == AsusData.NETWORK:
            _LOGGER.debug("Transforming network data")
            return transform_network(
                data,
                self.description,
                self._state.get(AsusData.NETWORK),
            )

        if datatype == AsusData.PORTS:
            _LOGGER.debug("Transforming port data")
            return transform_ethernet_ports(
                data,
                str(mac) if (mac := self.description.mac) else None,
            )

        if datatype == AsusData.WAN:
            _LOGGER.debug("Transforming WAN data")
            return transform_wan(
                data,
                self.support,
            )

        return data

    def _drop_data(self, datatype: AsusData, endpoint: EndpointType) -> bool:
        """Check whether data should be dropped.

        This is required for some data obtained from multiple endpoints.
        """

        if (
            datatype == AsusData.OPENVPN_CLIENT
            and self.description.firmware.firmware_type
            in (
                ARFirmwareType.MERLIN,
                ARFirmwareType.GNUTON,
            )
        ):
            return endpoint == Endpoint.HOOK

        return False

    def _check_prerequisites(self, datatype: AsusData) -> None:
        """Check prerequisites before fetching data."""

        _LOGGER.debug(
            "Triggered method _check_prerequisites for datatype `%s`", datatype
        )

        # A placeholder for future checks

    async def _check_postrequisites(self, datatype: AsusData) -> None:
        """Check postrequisites after fetching data.

        This method is also used to fetch additional data.
        """

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

    def _check_state(self, datatype: AsusData | None) -> None:
        """Make sure the state object is available."""

        _LOGGER.debug("Triggered method _check_state")

        if datatype is None:
            return

        # Add state object but make sure it's marked expired
        if datatype not in self._state:
            self._state[datatype] = AsusDataState(
                timestamp=datetime.now(UTC) - 2 * self._cache_threshold
            )

    def _return_state(self, datatype: AsusData, **kwargs: Any) -> Any:
        """Return a proper state."""

        _LOGGER.debug("Triggered method _return_state")

        # Get the state
        state = self._state[datatype].data

        if datatype == AsusData.PORTS:
            mac = self.description.mac
            own_mac = str(mac) if mac else None

            # Get the device selected
            device = kwargs.get("device")

            match device:
                case None:
                    if isinstance(state, dict):
                        return state.get(own_mac, {})
                    return state
                case "all":
                    return state
                # Case when substate is a MAC address
                case str() as a:
                    if isinstance(state, dict):
                        return state.get(a, {})
                    return {}

        return state

    def _get_callback_for_state(
        self, source: ARDataSource | ARDataType
    ) -> ARCallbackType | None:
        """Get a callback function for the specified state."""

        return self.async_api_load

    def _create_data_state(self, cllctn: ARDataCollection) -> bool:
        """Create a new data state if does not exist."""

        if not isinstance(cllctn, ARDataCollection) or not cllctn:
            return False

        # Check which items we don't have states for yet
        not_set = [item for item in cllctn if item not in self._data_states]
        if not not_set:
            return True

        for item in not_set:
            # Create a correct state
            state: ARDataState = (
                ARDataStateDynamic(item)
                if isinstance(item, ARDataSource)
                else ARDataStateStatic(item)
            )

            # Find and assign callback and callables for this state
            state.callback = self._get_callback_for_state(item)
            state.state_caller = ARCallReg.get_callable(
                item, name=AR_CALL_GET_STATE
            )
            state.translate_caller = ARCallReg.get_callable(
                item, name=AR_CALL_TRANSLATE_STATE
            )

            self._data_states[item] = state

        return True

    def _get_call_matrix(
        self,
        states: list[ARDataState],
    ) -> dict[tuple[ARCallableType, ARCallbackType], list[ARDataState]]:
        """Get a call matrix for the specified states."""

        matrix: dict[
            tuple[ARCallableType, ARCallbackType], list[ARDataState]
        ] = defaultdict(list)

        for state in states:
            caller = state.state_caller
            callback = state.callback

            if not caller or not callback:
                continue

            matrix[(caller, callback)].append(state)

        return matrix

    def _save_data_state(
        self,
        state: ARDataState,
        data: dict[ARDataSource | ARDataType, Any],
    ) -> None:
        """Save the data state for the specified state."""

        source = state.source
        if source in data:
            state.update(data[source])
            self._data_states[source] = state

    def _translate_multidata_raw(
        self,
        data: dict[ARDataSource | ARDataType, Any],
        states: list[ARDataState],
    ) -> None:
        """Save raw multicaller output for states without a translator."""

        for state in states:
            self._save_data_state(state, data)

    def _translate_multidata_batch(
        self,
        translator: ARCallableType,
        states: list[ARDataState],
        data: dict[ARDataSource | ARDataType, Any],
    ) -> None:
        """Translate a full multicaller result using a batch translator."""

        translated = translator(data)
        if not isinstance(translated, dict):
            _LOGGER.debug(
                "Translator %s returned %s instead of dict",
                getattr(translator, "__name__", repr(translator)),
                type(translated).__name__,
            )
            return

        for state in states:
            self._save_data_state(state, translated)

    def _translate_multidata_single(
        self,
        translator: ARCallableType,
        states: list[ARDataState],
        data: dict[ARDataSource | ARDataType, Any],
    ) -> None:
        """Translate individual state entries from multicaller output."""

        for state in states:
            state_source = state.source
            if state_source not in data:
                continue

            translated = translator(data[state_source])
            state.update(translated)
            self._data_states[state_source] = state

    def _translate_multidata(
        self,
        data: dict[ARDataSource | ARDataType, Any],
        states: list[ARDataState],
    ) -> None:
        """Translate data obtained from a multicaller."""

        if not isinstance(data, dict):
            _LOGGER.debug(  # type: ignore[unreachable]
                "Multicaller result must be a dict, got %s",
                type(data).__name__,
            )
            return

        translators: dict[ARCallableType | None, list[ARDataState]] = (
            defaultdict(list)
        )
        for state in states:
            translators[state.translate_caller].append(state)

        for translator, grouped_states in translators.items():
            if translator is None:
                self._translate_multidata_raw(data, grouped_states)
                continue

            if ARCallReg.get_callable_flag(translator):
                self._translate_multidata_batch(
                    translator,
                    grouped_states,
                    data,
                )
                continue

            self._translate_multidata_single(
                translator,
                grouped_states,
                data,
            )

    async def _async_refresh_data_state(
        self,
        cllctn: ARDataCollection,
        force: bool = False,
        **kwargs: Any,
    ) -> None:
        """Refresh the data state for the specified source."""

        if not isinstance(cllctn, ARDataCollection) or not cllctn:
            return

        # Get the states to work with
        data_states = self._data_states
        _states = [
            s for item in cllctn if (s := data_states.get(item)) is not None
        ]
        if not _states:
            return

        # Build call matrix
        matrix = self._get_call_matrix(_states)

        # Fetch the data
        for (caller, callback), states in matrix.items():
            sources = [state.source for state in states]

            multicaller = ARCallReg.get_callable_flag(caller)

            if multicaller is True:
                data = await caller(callback, sources, force=force, **kwargs)
                self._translate_multidata(data, states)

            else:
                for state in states:
                    source = state.source
                    data = await caller(
                        callback, source, force=force, **kwargs
                    )
                    translator = state.translate_caller
                    if translator:
                        data = translator(data)

                    state.update(data)
                    self._data_states[source] = state

    async def async_get_data_state(
        self,
        source: ARDataRequest,
        force: bool = False,
        **kwargs: Any,
    ) -> dict[ARDataSource | ARDataType, ARDataState]:
        """Get the full data state for the specified source."""

        # Convert source to a collection
        cllctn = ARDataCollection.from_value(source)
        if not cllctn:
            return {}

        # Create a state for the source if it doesn't exist
        self._create_data_state(cllctn)

        # Update the state
        await self._async_refresh_data_state(cllctn, force=force, **kwargs)

        # Return the state
        return {
            item: s
            for item in cllctn
            if (s := self._data_states.get(item)) is not None
        }

    async def async_get_data_v2(
        self,
        source: ARDataRequest,
        force: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Get data from the specified source."""

        _LOGGER.debug("Querying data V2")

        # Allow recursive calls
        kwargs["get_data_callback"] = self.async_get_data_v2

        # Get the new data state
        data_state = await self.async_get_data_state(
            source, force=force, **kwargs
        )
        if not data_state:
            return None

        # Return only fresh data
        result = {
            key: state.content
            for key, state in data_state.items()
            if state.is_fresh(self._cache_threshold)
        }
        return result or None

    async def async_get_data(  # noqa: C901, PLR0912, PLR0915
        self, datatype: AsusData, force: bool = False, **kwargs: Any
    ) -> Any:
        """Get data from the device."""

        # --- V2 COMPATIBILITY ---
        # This small switcher will allow gradual switching from v1 to v2 logic
        if isinstance(datatype, ARDataSource | ARDataType):
            return await self.async_get_data_v2(
                source=datatype, force=force, **kwargs
            )

        # Check if we have a state object for this data
        self._check_state(datatype)
        _state_dt = self._state[datatype]

        # If state object is active, wait for it to finish and return the data
        if _state_dt.active:
            try:
                _LOGGER.debug(
                    "Already in progress. Waiting for data to be fetched"
                )
                await asyncio.wait_for(
                    _state_dt.inactive_event.wait(),
                    DEFAULT_TIMEOUT,
                )
            except TimeoutError:
                _LOGGER.debug(
                    "Timeout while waiting for data. Will try fetching again"
                )

        # Check if we have the data already and not forcing a refresh
        if _state_dt.data and not force:
            # Check if the data is younger than the cache time
            if datetime.now(UTC) - _state_dt.timestamp < self._cache_threshold:
                _LOGGER.debug(
                    "Using cached data for `%s`: %s",
                    datatype,
                    _state_dt.data,
                )
                # Return the cached data
                return _state_dt.data
            _LOGGER.debug("Data for %s is too old. Fetching", datatype)

        # Mark the data as active
        _state_dt.start()

        # Check prerequisites
        self._check_prerequisites(datatype)

        # Get the data finder
        data_finder = self._where_to_get_data(datatype)

        # Check if we have a data finder
        if not data_finder:
            _LOGGER.debug("No data finder for %s", datatype)
            return {}

        result: dict[AsusData, Any] = {}

        df_request = data_finder.request
        df_method = data_finder.method
        df_arguments = data_finder.arguments
        df_merge = data_finder.merge
        description = self.description

        try:
            for endpoint in data_finder.endpoint:
                # Get the data from the endpoint
                request = "hook=" if endpoint == Endpoint.HOOK else ""
                for key, value in df_request:
                    request += f"{key}({value});"
                if df_method:
                    argument = self._get_attribute(df_arguments)
                    request += df_method(argument) if argument else df_method()

                # Add the request from kwargs
                kw_request = kwargs.get("request", {})
                if isinstance(kw_request, dict) and kw_request:
                    for key, value in kw_request.items():
                        request += f"{key}={value};"
                    # Remove trailing symbol
                    request = request[:-1]

                # Fetch the data
                data = await self.async_api_load(endpoint, request)

                processed = process(
                    endpoint,
                    data,
                    self._state,
                    description=description,
                )

                # Check whether data should be dropped
                processed = {
                    key: val
                    for key, val in processed.items()
                    if not self._drop_data(key, endpoint)
                }

                result = merge_dicts(result, processed)

                # Check if we have data and data finder merge is ANY
                if result and df_merge == AsusDataMerge.ANY:
                    break

            # Transform data if needed
            result = {
                key: self._transform_data(key, value)
                for key, value in result.items()
            }
            # Save the data state
            for key, value in result.items():
                state = self._state.get(key)
                if state is None:
                    state = AsusDataState()
                    self._state[key] = state
                state.update(value)
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
            type(_state_dt.data),
        )
        return self._return_state(datatype, **kwargs)

    # ---------------------------
    # Service-related methods -->
    # ---------------------------

    async def async_run_service(
        self,
        service: str | None,
        arguments: dict[str, Any] | None = None,
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
            self._async_drop_connection()

        return result

    async def _async_check_state_dependency(self, state: AsusState) -> None:
        """Check and queue state dependencies. Required for some states."""

        _LOGGER.debug("Triggered method _async_check_state_dependency")

        dependency = get_datatype(state)

        if dependency == AsusData.VPNC:
            # VPNC state change requires the correct previous state
            await self.async_get_data(AsusData.VPNC, force=True)

        elif dependency == AsusData.AURA:
            # Aura state change requires the correct previous state
            await self.async_get_data(AsusData.AURA, force=True)

    def _async_get_state_callback(
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

        _LOGGER.debug(
            "Triggered method async_set_state: `%s` with arguments `%s`."
            " Expecting modify: `%s`",
            state,
            kwargs,
            expect_modify,
        )

        # Check dependencies
        await self._async_check_state_dependency(state)

        # Get the state callback
        callback = self._async_get_state_callback(state)

        result = await set_state(
            callback=callback,
            state=state,
            expect_modify=expect_modify,
            router_state=self._state,
            identity=self.description,
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

    # If any of port forwarding methods gets removed,
    # notify in https://github.com/Vaskivskyi/asusrouter/issues/611
    # so that users of these methods will know of a breaking change

    async def async_apply_port_forwarding_rules(
        self,
        rules: list[PortForwardingRule],
    ) -> bool:
        """Apply port forwarding rules."""

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
        """Remove port forwarding rules."""

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
        """Set port forwarding rules."""

        rules = safe_list(rules)

        # Get current rules
        current_rules: list[PortForwardingRule] = (
            await self.async_get_data(AsusData.PORT_FORWARDING)
        )["rules"]

        # Make a copy to avoid modifying the original list
        current_rules = list(current_rules)

        # Add new rules
        current_rules.extend(rules)

        # Apply new rules
        return await self.async_apply_port_forwarding_rules(current_rules)

    # ---------------------------
    # <-- Legacy methods
    # ---------------------------

    # ---------------------------
    # Properties -->
    # ---------------------------

    @property
    def description(self) -> ARDeviceIdentity:
        """Return the device description."""

        state = self._data_states.get(ARDeviceSourceUniversal)
        if state and isinstance(content := state.content, ARDeviceIdentity):
            return content
        return ARDeviceIdentity()

    @property
    def support(self) -> dict[ARSupportType, Any]:
        """Return the device support data."""

        return self.description.support

    @property
    def connected(self) -> bool:
        """Return connection status."""

        return self._connection.connected if self._connection else False

    @property
    def config(self) -> ARInstanceConfig:
        """Return connection config."""

        return self._config

    @property
    def webpanel(self) -> str:
        """Return the web panel URL."""

        if self._connection:
            return self._connection.webpanel

        return (
            f"https://{self._hostname}:{self._port or DEFAULT_PORT_HTTPS}"
            if self._use_ssl
            else f"http://{self._hostname}:{self._port or DEFAULT_PORT_HTTP}"
        )

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

        if self._connection:
            self._connection.reset_connection()
            # await self._connection._async_close_session()

    # ---------------------------
    # <-- General management
    # ---------------------------
