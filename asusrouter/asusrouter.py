"""AsusRouter module.

This module contains the main class for interacting with an Asus device.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable
from datetime import UTC, datetime, timedelta
from functools import partial
import json
import logging
from typing import Any, Self

import aiohttp

from asusrouter.config import ARConfigKey as ARConfKey, ARInstanceConfig
from asusrouter.config.connection import (
    ARConnectionConfig,
    ARConnectionConfigKey as ARCCKey,
)
from asusrouter.connection import Connection
from asusrouter.const import (
    AR_CALL_GET_STATE,
    AR_CALL_TRANSLATE_STATE,
    DEFAULT_CACHE_TIME,
    DEFAULT_CACHE_TIME_V2,
    DEFAULT_TIMEOUT,
)
from asusrouter.error import (
    AsusRouter404Error,
    AsusRouterAccessError,
    AsusRouterConnectionError,
    AsusRouterDataError,
)
from asusrouter.modules.aimesh import ARAiMeshSourceUniversal
from asusrouter.modules.aimesh.topology import ARAiMeshTopology
from asusrouter.modules.boottime import ARBoottime, ARBoottimeSourceUniversal
from asusrouter.modules.data import AsusData, AsusDataState
from asusrouter.modules.data_finder import (
    ASUSDATA_MAP,
    ASUSDATA_NVRAM,
    AsusDataFinder,
    AsusDataMerge,
    add_conditional_data_alias,
    add_conditional_data_rule,
    remove_data_rule,
)
from asusrouter.modules.data_transform import transform_wan
from asusrouter.modules.device import ARDeviceSourceUniversal
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import process, read
from asusrouter.modules.endpoint.error import AccessError
from asusrouter.modules.endpoint_v2 import (
    AREndpoint,
    get_endpoint_reader,
    get_endpoint_request_type,
)
from asusrouter.modules.firmware import AR_FW_388, AR_FW_MERLIN_LIKE
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
    save_state,
    set_state,
)
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.modules.support.helpers import support_available
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools import legacy
from asusrouter.tools.converters import get_enum_key_by_value, safe_list
from asusrouter.tools.converters_v2.raw import raw_to_str
from asusrouter.tools.readers import merge_dicts
from asusrouter.tools.types import ARCallableType

_LOGGER = logging.getLogger(__name__)

_AUTH_RETRY_DELAY: int = 1

ARDataRequest = ARDataSource | ARDataType | Iterable[ARDataSource | ARDataType]


def _where_to_get_data(datatype: AsusData) -> AsusDataFinder | None:
    """Get the list of endpoints to get data from."""

    _LOGGER.debug("Triggered method _where_to_get_data")

    data_map = ASUSDATA_MAP.get(datatype)
    while isinstance(data_map, AsusData):
        data_map = ASUSDATA_MAP.get(data_map)
    if not isinstance(data_map, AsusDataFinder):
        _LOGGER.debug("No map found for %s", datatype)
        return None

    _LOGGER.debug("Endpoints to check: %s", data_map.endpoint)

    return data_map


def _get_call_matrix(
    states: list[ARDataState],
) -> dict[ARCallableType, list[ARDataState]]:
    """Group states by their caller into a call matrix."""

    matrix: dict[ARCallableType, list[ARDataState]] = defaultdict(list)

    for state in states:
        caller = state.state_caller
        if caller is None:
            continue
        matrix[caller].append(state)

    return matrix


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

        self._cache_threshold = timedelta(
            seconds=cache_time or DEFAULT_CACHE_TIME
        )
        self._cache_threshold_v2 = timedelta(seconds=DEFAULT_CACHE_TIME_V2)

        self._state: dict[AsusData, AsusDataState] = {}
        self._data_states: dict[ARDataSource | ARDataType, ARDataState] = {}

        # Endpoints that returned 404
        self._unavailable_endpoints: set[AREndpoint] = set()

        # Time for change to take effect before available to fetch
        self._needed_time: int | None = None
        # ID from the last called service
        self._last_id: int | None = None

        self._connection: Connection = Connection(
            hostname=hostname,
            username=username,
            password=password,
            port=port,
            use_ssl=use_ssl,
            session=session,
            timeout=DEFAULT_TIMEOUT,
            dumpback=dumpback,
            config=connection_config,
        )

    # ---------------------------
    # Properties -->
    # ---------------------------

    @property
    def description(self) -> ARDeviceIdentity:
        """Return the device description."""

        state = self._data_states.get(ARDeviceSourceUniversal)
        content = state.content if state else None
        if isinstance(content, ARDeviceIdentity):
            return content
        return ARDeviceIdentity()

    @property
    def support(self) -> dict[ARSupportType, Any]:
        """Return the device support data."""

        return self.description.support

    @property
    def connected(self) -> bool:
        """Return connection status."""

        return self._connection.connected

    @property
    def config(self) -> ARInstanceConfig:
        """Return instance configuration."""

        return self._config

    @property
    def connection_config(self) -> ARConnectionConfig:
        """Return connection configuration."""

        return self._connection.config

    @property
    def webpanel(self) -> str:
        """Return the web panel URL."""

        return self._connection.webpanel

    # ---------------------------
    # <-- Properties
    # ---------------------------

    # ---------------------------
    # Connection-related methods -->
    # ---------------------------

    async def __aenter__(self) -> Self:
        """Enter context manager and connect."""

        await self.async_connect()
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        """Exit context manager and close."""

        await self.async_close()

    async def async_close(self) -> None:
        """Disconnect from the device and close the connection."""

        _LOGGER.debug("Triggered method async_close")

        await self.async_disconnect()
        await self._connection.async_close_session()

    async def async_connect(self) -> bool:
        """Connect to the device and get its identity."""

        _LOGGER.debug("Triggered method async_connect")

        result = await self._connection.async_connect()
        if result is False:
            return False

        # Fresh connection — re-evaluate endpoint availability
        self._unavailable_endpoints.clear()

        # Fetch the device description
        result = await self.async_fetch_data(
            ARDeviceSourceUniversal, force=True
        )
        # Apply legacy conditional data rules only if description was fetched
        if result is not None:
            self._apply_v1_conditional_rules()
            # Seed the live AiMesh topology before any user request, so it
            # is available on the identity right after connecting
            await self.async_fetch_data(ARAiMeshSourceUniversal, force=True)
            # Boot time: use the seeded config value if given (anchors
            # stabilization), otherwise fetch it once now
            seeded_boottime = self._config.get(ARConfKey.BOOTTIME)
            if seeded_boottime is not None:
                self.description.update_boottime(seeded_boottime)
            else:
                await self.async_fetch_data(
                    ARBoottimeSourceUniversal, force=True
                )

        return result is not None

    async def async_disconnect(self) -> bool:
        """Disconnect from the device."""

        _LOGGER.debug("Triggered method async_disconnect")

        try:
            await self._connection.async_disconnect()
        except Exception as ex:  # noqa: BLE001
            self._handle_exception(ex)

        return True

    def _async_drop_connection(self) -> None:
        """Drop the connection.

        In case we know it cannot reply due to our last actions.
        """

        _LOGGER.debug("Triggered method _async_drop_connection")

        self._connection.reset_auth()

    def _handle_exception(self, ex: Exception) -> None:
        """Handle exceptions."""

        _LOGGER.debug("Triggered method _handle_exception")

        raise ex

    # ---------------------------
    # <-- Connection-related methods
    # ---------------------------

    # ---------------------------
    # Request-related methods -->
    # ---------------------------

    async def async_fetch(
        self,
        endpoint: AREndpoint,
        request: str | None = None,
    ) -> str | None:
        """Fetch raw string content from a V2 API endpoint."""

        _LOGGER.debug("Triggered method async_fetch: %s", endpoint)

        # Skip endpoints already known absent on this firmware
        if endpoint in self._unavailable_endpoints:
            _LOGGER.debug(
                "Endpoint %s is known unavailable, skipping", endpoint
            )
            return None

        request_type = get_endpoint_request_type(endpoint)

        for attempt in range(2):
            try:
                status, _, content = await self._connection.async_query(
                    endpoint, payload=request, request_type=request_type
                )
                _LOGGER.debug("Response %s from %s", status, endpoint)
                return content
            except AsusRouter404Error:
                _LOGGER.debug(
                    "Endpoint %s not found, marking unavailable", endpoint
                )
                self._unavailable_endpoints.add(endpoint)
                return None
            except AsusRouterAccessError as ex:
                if ex.args[1] != AccessError.AUTHORIZATION or attempt > 0:
                    raise
                self._async_drop_connection()
                await asyncio.sleep(_AUTH_RETRY_DELAY)

        return None

    async def async_read(
        self,
        endpoint: AREndpoint,
        request: str | None = None,
    ) -> dict[str, Any]:
        """Fetch and parse content from a V2 API endpoint."""

        _LOGGER.debug("Triggered method async_read: %s", endpoint)

        content = await self.async_fetch(endpoint, request)
        normalized = raw_to_str(content)
        if not normalized:
            return {}
        return get_endpoint_reader(endpoint)(normalized)

    # ---------------------------
    # <-- Request-related methods
    # ---------------------------

    # ---------------------------
    # Data pipeline -->
    # ---------------------------

    def _create_data_state(self, collection: ARDataCollection) -> None:
        """Create a new data state if does not exist."""

        if not isinstance(collection, ARDataCollection) or not collection:
            return

        data_states = self._data_states
        callback = self.async_read
        get_callable = ARCallReg.get_callable
        for item in collection:
            if item in data_states:
                continue

            state: ARDataState = (
                ARDataStateDynamic(item)
                if isinstance(item, ARDataSource)
                else ARDataStateStatic(item)
            )
            state.callback = callback
            state.state_caller = get_callable(item, name=AR_CALL_GET_STATE)
            state.translate_caller = get_callable(
                item, name=AR_CALL_TRANSLATE_STATE
            )
            data_states[item] = state

    def _commit_data_state(self, state: ARDataState, value: Any) -> None:
        """Update a state with new data and persist it."""

        state.update(value)
        self._data_states[state.source] = state
        # Keep the identity's live AiMesh topology in sync
        if isinstance(value, ARAiMeshTopology):
            self.description.update_aimesh(value)
        # Keep the identity's live boot time in sync
        elif isinstance(value, ARBoottime):
            self.description.update_boottime(value)

    def _translate_multidata_batch(
        self,
        translator: ARCallableType,
        states: list[ARDataState],
        data: dict[ARDataSource | ARDataType, Any],
        identity: ARDeviceIdentity,
    ) -> None:
        """Translate a full multicaller result using a batch translator."""

        translated = translator(data, identity=identity)
        if not isinstance(translated, dict):
            _LOGGER.debug(
                "Translator %s returned %s instead of dict",
                getattr(translator, "__name__", repr(translator)),
                type(translated).__name__,
            )
            return

        commit = self._commit_data_state
        for state in states:
            source = state.source
            if source in translated:
                commit(state, translated[source])

    def _translate_multidata_single(
        self,
        translator: ARCallableType,
        states: list[ARDataState],
        data: dict[ARDataSource | ARDataType, Any],
        identity: ARDeviceIdentity,
    ) -> None:
        """Translate individual state entries from multicaller output."""

        commit = self._commit_data_state
        for state in states:
            state_source = state.source
            if state_source not in data:
                continue

            commit(
                state,
                translator(data[state_source], identity=identity),
            )

    def _translate_multidata(
        self,
        states: list[ARDataState],
        data: dict[ARDataSource | ARDataType, Any],
        identity: ARDeviceIdentity,
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

        commit = self._commit_data_state
        get_callable_flag = ARCallReg.get_callable_flag
        for translator, grouped_states in translators.items():
            if translator is None:
                for state in grouped_states:
                    source = state.source
                    if source in data:
                        commit(state, data[source])
                continue

            if get_callable_flag(translator):
                self._translate_multidata_batch(
                    translator, grouped_states, data, identity
                )
                continue

            self._translate_multidata_single(
                translator, grouped_states, data, identity
            )

    async def _async_refresh_data_state(
        self,
        collection: ARDataCollection,
        force: bool = False,
        **kwargs: Any,
    ) -> None:
        """Refresh data states for all sources in the collection."""

        data_states = self._data_states
        threshold = self._cache_threshold_v2
        states = [
            s
            for item in collection
            if (s := data_states.get(item)) is not None
            and (force or not s.is_fresh(threshold))
        ]
        if not states:
            return

        matrix = _get_call_matrix(states)
        read = self.async_read
        get_callable_flag = ARCallReg.get_callable_flag
        commit = self._commit_data_state
        identity = self.description
        connection_config = self.connection_config

        for caller, caller_states in matrix.items():
            if get_callable_flag(caller):
                sources = [state.source for state in caller_states]
                data = await caller(
                    read,
                    sources,
                    force=force,
                    identity=identity,
                    connection_config=connection_config,
                    **kwargs,
                )
                self._translate_multidata(caller_states, data, identity)
            else:
                # Fan out concurrently; real concurrency is bounded by the
                # connection's request semaphore, so this stays device-safe
                raws = await asyncio.gather(
                    *(
                        caller(
                            read,
                            state.source,
                            force=force,
                            identity=identity,
                            connection_config=connection_config,
                            **kwargs,
                        )
                        for state in caller_states
                    )
                )
                for state, raw in zip(caller_states, raws):
                    translate = state.translate_caller
                    commit(
                        state,
                        translate(raw, identity=identity)
                        if translate
                        else raw,
                    )

    async def _async_get_data_state(
        self,
        source: ARDataRequest,
        force: bool = False,
        **kwargs: Any,
    ) -> dict[ARDataSource | ARDataType, ARDataState]:
        """Ensure, refresh, and return data states for the request."""

        collection = ARDataCollection.from_value(source)
        if not collection:
            return {}

        self._create_data_state(collection)
        await self._async_refresh_data_state(collection, force=force, **kwargs)

        data_states = self._data_states
        return {
            item: s
            for item in collection
            if (s := data_states.get(item)) is not None
        }

    async def async_fetch_data(
        self,
        source: ARDataRequest,
        force: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Fetch fresh data for the specified source."""

        _LOGGER.debug("Triggered method async_fetch_data")

        # Sub-fetches inherit this call's force (override per-call if needed)
        kwargs["get_data_callback"] = partial(
            self.async_fetch_data, force=force
        )
        # Raw fetch for readers that must see unparsed content
        kwargs["raw_callback"] = self.async_fetch

        data_state = await self._async_get_data_state(
            source, force=force, **kwargs
        )

        # Check for a reboot
        if self.description.rebooted:
            await self._async_handle_reboot()

        if not data_state:
            return None

        threshold = self._cache_threshold_v2
        result = {
            key: state.content
            for key, state in data_state.items()
            if state.is_fresh(threshold)
        }
        return result or None

    async def _async_handle_reboot(self) -> None:
        """Handle a detected device reboot (V2)."""

        _LOGGER.debug("Triggered method _async_handle_reboot")

        # TODO: Add LED recovery for v2

        self.description.clear_rebooted()

    # ---------------------------
    # <-- Data pipeline
    # ---------------------------

    # ---------------------------
    # V1 methods -->
    # ---------------------------

    def _apply_v1_conditional_rules(self) -> None:
        """Apply V1 conditional data rules based on device description."""

        _LOGGER.debug("Triggered method _apply_v1_conditional_rules")

        description = self.description
        firmware = description.firmware
        merlin = firmware.firmware_type in AR_FW_MERLIN_LIKE
        support = description.support

        if firmware > AR_FW_388:
            # Stock
            if not merlin:
                _LOGGER.debug("Adding conditional rules for stock firmware")
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
                        AREndpoint.FETCH_DATA,
                        nvram=ASUSDATA_NVRAM["openvpn_server_388"],
                    ),
                )
            # Merlin / Gnuton
            else:
                _LOGGER.debug("Adding conditional rules for Merlin firmware")
                add_conditional_data_rule(
                    AsusData.VPNC,
                    AsusDataFinder(
                        AREndpoint.FETCH_DATA,
                        nvram=ASUSDATA_NVRAM["vpnc"],
                    ),
                )
        # Before 388
        elif firmware < AR_FW_388:
            remove_data_rule(AsusData.VPNC)
            remove_data_rule(AsusData.VPNC_CLIENTLIST)
            remove_data_rule(AsusData.WIREGUARD)
            remove_data_rule(AsusData.WIREGUARD_CLIENT)
            remove_data_rule(AsusData.WIREGUARD_SERVER)

        if not support_available(support, ARSupportType.DSL):
            remove_data_rule(AsusData.DSL)

        if not support_available(support, ARSupportType.SPEEDTEST):
            remove_data_rule(AsusData.SPEEDTEST)
            remove_data_rule(AsusData.SPEEDTEST_RESULT)

    async def async_api_query(
        self, endpoint: AREndpoint, payload: str | None = None
    ) -> tuple[int, dict[str, str], str]:
        """Query the API endpoint."""

        _LOGGER.debug(
            "Triggered method async_api_query: %s | %s", endpoint, payload
        )

        return await self._connection.async_query(
            endpoint, payload, request_type=get_endpoint_request_type(endpoint)
        )

    async def async_api_load(
        self,
        endpoint: AREndpoint,
        request: str = "",
        retry: int = 0,
    ) -> dict[str, Any]:
        """Load API endpoint with optional request."""

        _LOGGER.debug("Triggered method async_api_load: %s", endpoint)

        try:
            status, _, content = await self.async_api_query(endpoint, request)
        except AsusRouter404Error:
            _LOGGER.debug("Endpoint %s not found", endpoint)
            return {}
        except AsusRouterAccessError as ex:
            if ex.args[1] == AccessError.AUTHORIZATION:
                self._async_drop_connection()
                await asyncio.sleep(1 + retry * 3)
                return await self.async_api_load(endpoint, request, 1)
            raise

        _LOGGER.debug("Response %s received from %s", status, endpoint)

        try:
            result = read(endpoint, content, config=self.config)
        except json.JSONDecodeError as ex:
            _LOGGER.debug(
                "Failed to read content from %s: %s", endpoint, content
            )
            if not retry:
                return await self.async_api_load(endpoint, request, 1)
            raise AsusRouterDataError(
                "Something went wrong while reading the content"
            ) from ex

        if result.get("run_service") in ("restart_httpd", "reboot"):
            self._async_drop_connection()

        return result

    async def async_api_hook(self, request: str) -> dict[str, Any]:
        """Perform a hook to the device API."""

        _LOGGER.debug("Triggered method async_api_hook: %s", request)

        return await self.async_api_load(
            endpoint=AREndpoint.FETCH_DATA,
            request=f"hook={request}",
        )

    async def async_api_command(
        self,
        commands: dict[str, str] | None,
        endpoint: AREndpoint = AREndpoint.PUSH_DATA,
    ) -> dict[str, Any]:
        """Send a command to the device."""

        _LOGGER.debug(
            "Triggered method async_api_command: %s | %s", endpoint, commands
        )

        return await self.async_api_load(
            endpoint=endpoint,
            request=str(commands),
        )

    def _transform_data(self, datatype: AsusData, data: Any) -> Any:
        """Transform data if needed."""

        _LOGGER.debug("Triggered method _transform_data for `%s`", datatype)

        description = self.description

        if datatype == AsusData.WAN:
            return transform_wan(
                data,
                description.support,
            )

        return data

    def _drop_data(self, datatype: AsusData, endpoint: AREndpoint) -> bool:
        """Check whether data should be dropped."""

        if (
            datatype == AsusData.OPENVPN_CLIENT
            and self.description.firmware.firmware_type in AR_FW_MERLIN_LIKE
        ):
            return endpoint == AREndpoint.FETCH_DATA

        return False

    async def _check_postrequisites(self, datatype: AsusData) -> None:
        """Check postrequisites after fetching data."""

        _LOGGER.debug(
            "Triggered method _check_postrequisites for datatype `%s`",
            datatype,
        )

        if datatype == AsusData.FIRMWARE:
            firmware = self._state[AsusData.FIRMWARE].data
            if firmware and firmware["state"] is True:
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

        if datatype not in self._state:
            self._state[datatype] = AsusDataState(
                timestamp=datetime.now(UTC) - 2 * self._cache_threshold
            )

    def _return_state(self, datatype: AsusData, **kwargs: Any) -> Any:
        """Return a proper state."""

        _LOGGER.debug("Triggered method _return_state")

        return self._state[datatype].data

    async def async_get_data(  # noqa: C901, PLR0912, PLR0915
        self, datatype: AsusData, force: bool = False, **kwargs: Any
    ) -> Any:
        """Get data from the device."""

        # --- V2 COMPATIBILITY ---
        if isinstance(datatype, ARDataSource | ARDataType):
            return await self.async_fetch_data(
                source=datatype, force=force, **kwargs
            )

        self._check_state(datatype)
        _state = self._state
        state_dt = _state[datatype]

        if state_dt.active:
            try:
                _LOGGER.debug(
                    "Already in progress. Waiting for data to be fetched"
                )
                await asyncio.wait_for(
                    state_dt.inactive_event.wait(),
                    DEFAULT_TIMEOUT,
                )
            except TimeoutError:
                _LOGGER.debug(
                    "Timeout while waiting for data. Will try fetching again"
                )

        if state_dt.data and not force:
            if datetime.now(UTC) - state_dt.timestamp < self._cache_threshold:
                _LOGGER.debug(
                    "Using cached data for `%s`: %s",
                    datatype,
                    state_dt.data,
                )
                return state_dt.data
            _LOGGER.debug("Data for %s is too old. Fetching", datatype)

        state_dt.start()

        data_finder = _where_to_get_data(datatype)

        if not data_finder:
            _LOGGER.debug("No data finder for %s", datatype)
            return {}

        result: dict[AsusData, Any] = {}

        df_request = data_finder.request
        df_method = data_finder.method
        df_merge = data_finder.merge
        description = self.description
        drop_data = self._drop_data
        transform_data = self._transform_data

        kw_raw = kwargs.get("request", {})
        kw_extra = (
            ";".join(f"{k}={v}" for k, v in kw_raw.items())
            if isinstance(kw_raw, dict) and kw_raw
            else ""
        )

        try:
            for endpoint in data_finder.endpoint:
                request = "hook=" if endpoint == AREndpoint.FETCH_DATA else ""
                request += "".join(f"{k}({v});" for k, v in df_request)
                if df_method and (method_result := df_method(description)):
                    request += method_result
                if kw_extra:
                    request += kw_extra

                data = await self.async_api_load(endpoint, request)

                processed = process(
                    endpoint,
                    data,
                    _state,
                    description=description,
                )

                processed = {
                    key: val
                    for key, val in processed.items()
                    if not drop_data(key, endpoint)
                }

                result = merge_dicts(result, processed)

                if result and df_merge == AsusDataMerge.ANY:
                    break

            result = {
                key: transform_data(key, value)
                for key, value in result.items()
            }
            for key, value in result.items():
                state = _state.get(key)
                if state is None:
                    state = AsusDataState()
                    _state[key] = state
                state.update(value)
        except (AsusRouterConnectionError, AsusRouterDataError):
            return self._return_state(datatype, **kwargs)

        await self._check_postrequisites(datatype)

        _LOGGER.debug(
            "Returning data for `%s` with object type `%s`",
            datatype,
            type(state_dt.data),
        )
        return self._return_state(datatype, **kwargs)

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

        if dependency in (AsusData.VPNC, AsusData.AURA):
            # State change requires the correct previous state
            await self.async_get_data(dependency, force=True)

    def _async_get_state_callback(
        self, state: AsusState
    ) -> Callable[..., Awaitable]:
        """Get the state callback."""

        _LOGGER.debug("Triggered method _async_get_state_callback")

        if get_datatype(state) == AsusData.AURA:
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

        await self._async_check_state_dependency(state)

        callback = self._async_get_state_callback(state)

        result = await set_state(
            callback=callback,
            state=state,
            expect_modify=expect_modify,
            router_state=self._state,
            identity=self.description,
            **kwargs,
        )

        if result is True:
            datatype = get_datatype(state)

            if datatype in (AsusData.VPNC, AsusData.AURA):
                # The only way to make it work with VPN Fusion
                await asyncio.sleep(1)
                await self._async_check_state_dependency(state)
            elif (
                get_enum_key_by_value(
                    AsusState, type(state), default=AsusState.NONE
                )
                != AsusState.PC_RULE
            ):
                self._check_state(datatype)
                _LOGGER.debug(
                    "Saving state `%s` for `%s` s with id=`%s`",
                    state,
                    self._needed_time,
                    self._last_id,
                )
                save_state(
                    state, self._state, self._needed_time, self._last_id
                )
                self._needed_time = None
                self._last_id = None

        return result

    # ---------------------------
    # <-- V1 methods
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

        current_rules: list[PortForwardingRule] = (
            await self.async_get_data(AsusData.PORT_FORWARDING)
        )["rules"]

        current_rules = [
            rule for rule in current_rules if rule.ip_address not in ips
        ]
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

        if apply:
            await self.async_apply_port_forwarding_rules(current_rules)

        return current_rules

    async def async_set_port_forwarding_rules(
        self,
        rules: PortForwardingRule | list[PortForwardingRule],
    ) -> bool:
        """Set port forwarding rules."""

        rules = safe_list(rules)

        current_rules: list[PortForwardingRule] = (
            await self.async_get_data(AsusData.PORT_FORWARDING)
        )["rules"]

        # Make a copy to avoid modifying the original list
        current_rules = list(current_rules)

        current_rules.extend(rules)

        return await self.async_apply_port_forwarding_rules(current_rules)

    # ---------------------------
    # <-- Legacy methods
    # ---------------------------
