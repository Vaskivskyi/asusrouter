"""AsusRouter module.

This module contains the main class for interacting with an Asus device.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable
from datetime import timedelta
from functools import partial
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
    AR_CALL_RUN_ACTION,
    AR_CALL_TRANSLATE_ACTION,
    AR_CALL_TRANSLATE_STATE,
    DEFAULT_CACHE_TIME_V2,
    DEFAULT_TIMEOUT,
)
from asusrouter.error import (
    AsusRouter404Error,
    AsusRouterAccessError,
    AsusRouterError,
)
from asusrouter.modules.action import ARAction
from asusrouter.modules.aimesh import ARAiMeshSourceUniversal
from asusrouter.modules.aimesh.topology import ARAiMeshTopology
from asusrouter.modules.boottime import ARBoottime, ARBoottimeSourceUniversal
from asusrouter.modules.device import ARDeviceSourceUniversal
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint.error import AccessError
from asusrouter.modules.endpoint_v2 import (
    AREndpoint,
    get_endpoint_reader,
    get_endpoint_request_type,
)
from asusrouter.modules.led import ARLedAction, async_recover_state
from asusrouter.modules.source import (
    ARDataCollection,
    ARDataSource,
    ARDataState,
    ARDataStateDynamic,
    ARDataStateStatic,
    ARDataType,
)
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters_v2.raw import raw_to_str
from asusrouter.tools.identifiers import Hostname
from asusrouter.tools.security.log import register_log_config
from asusrouter.tools.types import ARCallableType

_LOGGER = logging.getLogger(__name__)

_AUTH_RETRY_DELAY: int = 1

# Reboot recovery: grace before the first probe
_REBOOT_RECOVERY_INITIAL_DELAY: int = 30
_REBOOT_RECOVERY_TIMEOUT: int = 300
_REBOOT_RECOVERY_INTERVAL: int = 10

ARDataRequest = ARDataSource | ARDataType | Iterable[ARDataSource | ARDataType]


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
        session: aiohttp.ClientSession | None = None,
        dumpback: Callable[..., Awaitable[None]] | None = None,
        config: dict[ARConfKey, Any] | None = None,
        connection_config: dict[ARCCKey, Any] | None = None,
    ):
        """Initialize the interface."""

        _LOGGER.debug(
            "Initializing a new interface to `%s`", Hostname(hostname)
        )

        # Initialize configs
        _LOGGER.debug("Setting up AR instance config: %s", config)
        self._config = ARInstanceConfig(defaults=config)
        # Constrain shared log masking by this instance's log level
        register_log_config(self._config)

        self._cache_threshold_v2 = timedelta(seconds=DEFAULT_CACHE_TIME_V2)

        self._data_states: dict[ARDataSource | ARDataType, ARDataState] = {}

        # Endpoints that returned 404
        self._unavailable_endpoints: set[AREndpoint] = set()

        # In-flight reboot recovery; holds all requests until it finishes
        self._reboot_recovery: asyncio.Task[None] | None = None
        # Last commanded LED state, reasserted after a reboot (for Merlin)
        self._led_state: bool | None = None

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
        if result is not None:
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

        # Hold every request while recovering from a reboot
        recovery = self._reboot_recovery
        if recovery is not None:
            await recovery

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
        get_callable_flag = ARCallReg.get_callable_flag
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
            state.state_caller_multi = get_callable_flag(
                item, name=AR_CALL_GET_STATE
            )
            state.translate_caller = get_callable(
                item, name=AR_CALL_TRANSLATE_STATE
            )
            state.translate_caller_multi = get_callable_flag(
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
        for translator, grouped_states in translators.items():
            if translator is None:
                for state in grouped_states:
                    source = state.source
                    if source in data:
                        commit(state, data[source])
                continue

            if grouped_states[0].translate_caller_multi:
                self._translate_multidata_batch(
                    translator, grouped_states, data, identity
                )
                continue

            self._translate_multidata_single(
                translator, grouped_states, data, identity
            )

    async def _async_refresh_multi(
        self,
        caller: ARCallableType,
        states: list[ARDataState],
        identity: ARDeviceIdentity,
        **kwargs: Any,
    ) -> None:
        """Fetch and translate a multicaller group in one batched request."""

        sources = [state.source for state in states]
        try:
            data = await caller(
                self.async_read,
                sources,
                identity=identity,
                **kwargs,
            )
            self._translate_multidata(states, data, identity)
        finally:
            # Wake waiters as soon as this batch is done
            for state in states:
                state.end_refresh()

    async def _async_refresh_single(
        self,
        caller: ARCallableType,
        state: ARDataState,
        identity: ARDeviceIdentity,
        **kwargs: Any,
    ) -> None:
        """Fetch, translate and commit a single state."""

        try:
            raw = await caller(
                self.async_read,
                state.source,
                identity=identity,
                **kwargs,
            )
            translate = state.translate_caller
            self._commit_data_state(
                state,
                translate(raw, identity=identity) if translate else raw,
            )
        finally:
            # Wake waiters as soon as this fetch is done
            state.end_refresh()

    async def _async_refresh_states(
        self,
        states: list[ARDataState],
        **kwargs: Any,
    ) -> None:
        """Fetch all the given states, fanning out caller groups."""

        matrix = _get_call_matrix(states)
        identity = self.description
        kwargs["connection_config"] = self.connection_config

        # Fan out all caller groups concurrently; real concurrency is
        # bounded by the connection's request semaphore, device-safe
        tasks = []
        for caller, caller_states in matrix.items():
            if caller_states[0].state_caller_multi:
                tasks.append(
                    self._async_refresh_multi(
                        caller, caller_states, identity, **kwargs
                    )
                )
            else:
                tasks.extend(
                    self._async_refresh_single(
                        caller, state, identity, **kwargs
                    )
                    for state in caller_states
                )

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            # Safety net: each task ends its own states' refresh above so
            # in-gather waiters wake promptly
            for state in states:
                state.end_refresh()
        for result in results:
            if isinstance(result, BaseException):
                raise result

    async def _async_refresh_data_state(
        self,
        collection: ARDataCollection,
        force: bool = False,
        **kwargs: Any,
    ) -> None:
        """Refresh data states for all sources in the collection."""

        data_states = self._data_states
        threshold = self._cache_threshold_v2

        # Split into states to refresh here and states already being
        # refreshed by a concurrent caller (awaited instead of refetched)
        states: list[ARDataState] = []
        pending: list[ARDataState] = []
        for item in collection:
            state = data_states.get(item)
            if state is None:
                continue
            if state.refreshing:
                pending.append(state)
            elif force or not state.is_fresh(threshold):
                state.begin_refresh()
                states.append(state)

        if states:
            await self._async_refresh_states(states, force=force, **kwargs)

        # Wait for refreshes started by concurrent callers (after our own
        # fetches, so two interdependent callers cannot deadlock)
        if pending:
            await asyncio.gather(
                *(state.async_wait_refresh() for state in pending)
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
        # Let a fetch module trigger an action while resolving its data
        kwargs["run_action_callback"] = self.async_run_action

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

    async def async_run_action(self, action: ARAction, **kwargs: Any) -> Any:
        """Run an action or push data to the device."""

        _LOGGER.debug("Triggered method async_run_action: %s", action)

        run_caller = ARCallReg.get_callable(action, AR_CALL_RUN_ACTION)
        if run_caller is None:
            return None

        kwargs["get_data_callback"] = partial(
            self.async_fetch_data, force=True
        )
        kwargs["raw_callback"] = self.async_fetch
        kwargs["run_action_callback"] = self.async_run_action
        kwargs["expire_callback"] = self._async_expire_data

        raw = await run_caller(
            self.async_read, action, identity=self.description, **kwargs
        )

        # Remember the last commanded LED state
        if isinstance(action, ARLedAction) and raw:
            self._led_state = action.state

        # An action may have triggered a reboot
        if self.description.rebooted:
            self._async_drop_connection()
            if self._reboot_recovery is None:
                self._reboot_recovery = asyncio.create_task(
                    self._async_recover_after_reboot()
                )

        translate_caller = ARCallReg.get_callable(
            action, AR_CALL_TRANSLATE_ACTION
        )
        if translate_caller is None:
            return raw
        return translate_caller(raw, identity=self.description, **kwargs)

    async def _async_expire_data(
        self, source: ARDataSource | ARDataType
    ) -> None:
        """Expire a cached data state so its next read refetches."""

        state = self._data_states.get(source)
        if state is not None:
            state.expire()

    async def _async_handle_reboot(self) -> None:
        """Handle a detected device reboot (V2)."""

        _LOGGER.debug("Triggered method _async_handle_reboot")

        self.description.clear_rebooted()

        # Recover LED off for Merlin
        await async_recover_state(
            self.async_run_action, self._led_state, identity=self.description
        )

    async def _async_recover_after_reboot(self) -> None:
        """Hold requests while the device reboots, until it is back online."""

        _LOGGER.warning(
            "Device is rebooting; data fetching is on hold until it is back"
        )

        # Login attempts against a rebooting device are expected to fail
        self._connection.set_error_suppression(True)
        try:
            # Let the device actually go down before the first probe
            await asyncio.sleep(_REBOOT_RECOVERY_INITIAL_DELAY)

            loop = asyncio.get_running_loop()
            deadline = loop.time() + _REBOOT_RECOVERY_TIMEOUT
            while loop.time() < deadline:
                try:
                    reconnected = await self._connection.async_connect(
                        block_error=True
                    )
                except AsusRouterError:
                    reconnected = False
                if reconnected:
                    _LOGGER.debug("Device is back online after the reboot")
                    self.description.clear_rebooted()
                    return
                await asyncio.sleep(_REBOOT_RECOVERY_INTERVAL)

            _LOGGER.error(
                "Device did not come back within %ss after the reboot",
                _REBOOT_RECOVERY_TIMEOUT,
            )
        finally:
            self._connection.set_error_suppression(False)
            self._reboot_recovery = None

    # ---------------------------
    # <-- Data pipeline
    # ---------------------------
