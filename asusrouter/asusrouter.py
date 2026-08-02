"""AsusRouter module.

This module contains the main class for interacting with an Asus device.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable
from datetime import datetime, timedelta
from functools import partial
import logging
from pathlib import Path
from typing import Any, Self

import aiohttp

from asusrouter.config import ARConfigKey as ARConfKey, ARInstanceConfig
from asusrouter.config.connection import (
    ARConnectionConfig,
    ARConnectionConfigKey as ARCCKey,
)
from asusrouter.connection import Connection
from asusrouter.const import (
    AR_CALL_FETCH_STATE,
    AR_CALL_PROBE_STATE,
    AR_CALL_RUN_ACTION,
    AR_CALL_TRANSLATE_ACTION,
    AR_CALL_TRANSLATE_STATE,
    DEFAULT_CACHE_TIME,
    DEFAULT_TIMEOUT,
)
from asusrouter.error import (
    AsusRouter404Error,
    AsusRouterAccessError,
    AsusRouterError,
)
from asusrouter.modules import load_all_probes, load_all_sources
from asusrouter.modules.action import ARAction
from asusrouter.modules.aimesh import ARAiMeshSourceUniversal
from asusrouter.modules.aimesh.topology import ARAiMeshTopology
from asusrouter.modules.clock import (
    ARBoottime,
    ARClockField,
    ARClockSource,
    ARClockSourceUniversal,
)
from asusrouter.modules.device import ARDeviceSourceUniversal
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import (
    AREndpoint,
    get_endpoint_reader,
    get_endpoint_request_type,
)
from asusrouter.modules.endpoint.error import ARAccessError
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
from asusrouter.tools.converters.raw import raw_to_str
from asusrouter.tools.dump import (
    DEFAULT_DUMP_PATH,
    DUMP_SENSITIVE_WARNING,
    ARDumpRecorder,
    active_recorder,
    bind_recorder,
    unbind_recorder,
    write_device_snapshot,
    write_dump,
)
from asusrouter.tools.identifiers import Hostname, Username
from asusrouter.tools.probe import (
    DEFAULT_PROBE_PATH,
    PROBE_SENSITIVE_WARNING,
    ARProbeReport,
    ARProbeSection,
    write_probe,
)
from asusrouter.tools.readers import is_redirect_page
from asusrouter.tools.security import ARSecurityLevel
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
        response_callback: Callable[..., Awaitable[None]] | None = None,
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

        self._username = Username(username)

        self._cache_threshold = timedelta(seconds=DEFAULT_CACHE_TIME)

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
            response_callback=response_callback,
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

    async def _async_ensure_connected(self) -> None:
        """Connect and identify before a request if not connected."""

        if self._reboot_recovery is None and not self._connection.connected:
            _LOGGER.debug("Not connected yet; connecting before the request")
            await self.async_connect()

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
            # Inject username
            self.description.update_username(self._username)
            # Seed the live AiMesh topology before any user request, so it
            # is available on the identity right after connecting
            await self.async_fetch_data(ARAiMeshSourceUniversal, force=True)
            # A seeded boot time anchors the first stabilization
            seeded_boottime = self._config.get(ARConfKey.BOOTTIME)
            if seeded_boottime is not None:
                self.description.update_boottime(seeded_boottime)
            await self.async_fetch_data(ARClockSourceUniversal, force=True)

        return result is not None

    async def async_disconnect(self) -> bool:
        """Disconnect from the device."""

        _LOGGER.debug("Triggered method async_disconnect")

        try:
            await self._connection.async_disconnect()
        except Exception as ex:  # noqa: BLE001
            self._handle_exception(ex)

        return True

    def _current_credentials(self) -> tuple[str, str]:
        """Return the (username, password) currently held by the connection."""

        return self._connection.username, self._connection.password

    async def _async_set_credentials(
        self, username: str, password: str
    ) -> bool:
        """Swap the login credentials and re-establish the session."""

        _LOGGER.debug("Triggered method _async_set_credentials")

        return await self._connection.async_set_credentials(username, password)

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
                # Legacy can return a 200 with redirect instead of 404
                if is_redirect_page(content):
                    _LOGGER.debug(
                        "Endpoint %s returned a redirect, marking unavailable",
                        endpoint,
                    )
                    self._unavailable_endpoints.add(endpoint)
                    return None
                recorder = active_recorder()
                if recorder is not None:
                    recorder.record(endpoint, request_type, request, content)
                return content
            except AsusRouter404Error:
                _LOGGER.debug(
                    "Endpoint %s not found, marking unavailable", endpoint
                )
                self._unavailable_endpoints.add(endpoint)
                return None
            except AsusRouterAccessError as ex:
                if ex.args[1] != ARAccessError.AUTHORIZATION or attempt > 0:
                    raise
                self._async_drop_connection()
                await asyncio.sleep(_AUTH_RETRY_DELAY)

        # Unreachable: the retry loop always returns or raises
        return None

    async def async_read(
        self,
        endpoint: AREndpoint,
        request: str | None = None,
    ) -> Any:
        """Fetch and parse content."""

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
            state.state_caller = get_callable(item, name=AR_CALL_FETCH_STATE)
            state.state_caller_multi = get_callable_flag(
                item, name=AR_CALL_FETCH_STATE
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
        # Keep the identity's live clock in sync
        elif isinstance(state.source, ARClockSource) and isinstance(
            value, dict
        ):
            self._sync_clock(value)

    def _sync_clock(self, value: dict[Any, Any]) -> None:
        """Sync the identity with the values a clock read reported."""

        boottime = value.get(ARClockField.BOOTTIME)
        if isinstance(boottime, ARBoottime):
            self.description.update_boottime(boottime)

        uptime = value.get(ARClockField.UPTIME)
        # `bool` is an `int`; only a real count says anything here
        if isinstance(uptime, int) and not isinstance(uptime, bool):
            self.description.update_uptime(uptime)

        device_time = value.get(ARClockField.DEVICE_TIME)
        if (
            isinstance(device_time, datetime)
            and device_time.tzinfo is not None
        ):
            self.description.update_device_time(device_time)

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
                # Allow continuous translation/read
                translate(raw, identity=identity, previous=state.content)
                if translate
                else raw,
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
        threshold = self._cache_threshold

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

        await self._async_ensure_connected()

        # Sub-fetches inherit this call's force (override per-call if needed)
        kwargs["fetch_data_callback"] = partial(
            self.async_fetch_data, force=force
        )
        # Raw fetch for readers that must see unparsed content
        kwargs["fetch_raw_callback"] = self.async_fetch
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

        threshold = self._cache_threshold
        result = {
            key: state.content
            for key, state in data_state.items()
            if state.is_fresh(threshold)
        }
        return result or None

    # ---------------------------
    # <-- Data pipeline
    # ---------------------------

    # ---------------------------
    # Data dump -->
    # ---------------------------

    def _warn_dump_once(self) -> None:
        """Emit the sensitive-data warning once per session."""

        config = self._config
        config.ensure_notification_flag(ARConfKey.NOTIFIED_DUMP)
        if not config.get(ARConfKey.NOTIFIED_DUMP):
            _LOGGER.warning(DUMP_SENSITIVE_WARNING)
            config.set(ARConfKey.NOTIFIED_DUMP, True)

    def _default_sources(self) -> list[ARDataSource]:
        """Build the default instance of every fetchable source."""

        # Import all modules to register sources
        load_all_sources()

        sources: list[ARDataSource] = []
        for source_cls in sorted(
            ARCallReg.classes_with(AR_CALL_FETCH_STATE),
            key=lambda cls: cls.__name__,
        ):
            if not issubclass(source_cls, ARDataSource):
                continue
            try:
                sources.append(source_cls())
            except TypeError:
                _LOGGER.debug(
                    "Skipping source without a default instance: %s",
                    source_cls.__name__,
                )
        return sources

    async def _async_dump_source(
        self, source: ARDataSource | ARDataType, path: str | Path
    ) -> Path | None:
        """Dump a single source's raw replies, if any were captured."""

        recorder = ARDumpRecorder()
        # Bind to the async context so only this dump's own fetches (and their
        # context-inheriting sub-tasks) are captured, never concurrent traffic
        token = bind_recorder(recorder)
        try:
            await self.async_fetch_data(source, force=True)
        finally:
            unbind_recorder(token)

        if not recorder:
            return None
        return write_dump(
            recorder, path=path, identity=self.description, source=source
        )

    async def async_dump_data(
        self,
        source: ARDataRequest,
        path: str | Path = DEFAULT_DUMP_PATH,
    ) -> list[Path]:
        """Dump raw device replies for the given source(s) to disk."""

        self._warn_dump_once()

        collection = ARDataCollection.from_value(source)
        if not collection:
            return []

        written: list[Path] = []
        for item in collection:
            result = await self._async_dump_source(item, path)
            if result is not None:
                written.append(result)
        if written:
            write_device_snapshot(path, self.description)
        return written

    async def async_dump_all(
        self, path: str | Path = DEFAULT_DUMP_PATH
    ) -> list[Path]:
        """Dump raw replies for every default source in one pass."""

        self._warn_dump_once()

        written: list[Path] = []
        for item in self._default_sources():
            try:
                result = await self._async_dump_source(item, path)
            except AsusRouterError:
                _LOGGER.exception(
                    "Failed to dump source %s", type(item).__name__
                )
                continue
            if result is not None:
                written.append(result)
        if written:
            write_device_snapshot(path, self.description)
        return written

    # ---------------------------
    # <-- Data dump
    # ---------------------------

    # ---------------------------
    # Device probe -->
    # ---------------------------

    def _warn_probe_once(self) -> None:
        """Emit the redaction warning once per session."""

        config = self._config
        config.ensure_notification_flag(ARConfKey.NOTIFIED_PROBE)
        if not config.get(ARConfKey.NOTIFIED_PROBE):
            _LOGGER.warning(PROBE_SENSITIVE_WARNING)
            config.set(ARConfKey.NOTIFIED_PROBE, True)

    async def async_probe_data(
        self,
        source: ARDataSource | ARDataType,
        *,
        path: str | Path | None = DEFAULT_PROBE_PATH,
        level: ARSecurityLevel = ARSecurityLevel.SANITIZED,
        **kwargs: Any,
    ) -> ARProbeReport | None:
        """Probe a source and report what it produced."""

        _LOGGER.debug("Triggered method async_probe_data: %s", source)

        # Import the probes only when one is actually asked for
        load_all_probes()

        probe_caller = ARCallReg.get_callable(source, AR_CALL_PROBE_STATE)
        if probe_caller is None:
            _LOGGER.debug(
                "No probe registered for source %s", type(source).__name__
            )
            return None

        self._warn_probe_once()
        await self._async_ensure_connected()

        # A probe reads the device as it is now, never a cached state
        kwargs["fetch_data_callback"] = partial(
            self.async_fetch_data, force=True
        )
        kwargs["fetch_raw_callback"] = self.async_fetch
        kwargs["run_action_callback"] = self.async_run_action

        sections: list[ARProbeSection] = await probe_caller(
            self.async_read,
            source,
            identity=self.description,
            level=level,
            **kwargs,
        )

        report = ARProbeReport(
            source=type(source).__name__,
            level=level,
            sections=tuple(sections),
        )

        if path is not None:
            write_probe(report, path=path, identity=self.description)

        return report

    # ---------------------------
    # <-- Device probe
    # ---------------------------

    # ---------------------------
    # Action pipeline -->
    # ---------------------------

    async def async_run_action(self, action: ARAction, **kwargs: Any) -> Any:
        """Run an action or push data to the device."""

        _LOGGER.debug("Triggered method async_run_action: %s", action)

        run_caller = ARCallReg.get_callable(action, AR_CALL_RUN_ACTION)
        if run_caller is None:
            return None

        await self._async_ensure_connected()

        kwargs["fetch_data_callback"] = partial(
            self.async_fetch_data, force=True
        )
        kwargs["fetch_raw_callback"] = self.async_fetch
        kwargs["run_action_callback"] = self.async_run_action
        kwargs["expire_callback"] = self._async_expire_data
        kwargs["credentials_get_callback"] = self._current_credentials
        kwargs["credentials_set_callback"] = self._async_set_credentials

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
    # <-- Action pipeline
    # ---------------------------
