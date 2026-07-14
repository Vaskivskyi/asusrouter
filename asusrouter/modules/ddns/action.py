"""DDNS action for AsusRouter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import logging
from typing import Any

from asusrouter.modules.action import ARAction
from asusrouter.modules.common.command import ARActionMode, ARService
from asusrouter.modules.ddns.enums import (
    ARDdnsCommand,
    ARDdnsField,
    ARDdnsServer,
    ARDdnsStatus,
)
from asusrouter.modules.ddns.source import (
    DDNS_REQUEST,
    ARDdnsSourceUniversal,
    read_status,
)
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.endpoint.hooks import hook_request, hook_value
from asusrouter.modules.nvram import ARNvramType, async_expire_values
from asusrouter.modules.service.action import (
    ARServiceResult,
    async_run_service,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters_v2.raw import raw_to_bool, raw_to_int
from asusrouter.tools.identifiers import Password
from asusrouter.tools.poll import async_poll_until
from asusrouter.tools.types import ARCallbackType

_LOGGER = logging.getLogger(__name__)

# The config shares the shape the read source emits, for a clean round-trip
ARDdnsConfig = dict[ARDdnsField, Any]

# The action type reported in `asusddns_reg_result` by a deregistration
_UNREGISTER_PREFIX = "unregister,"
# Deregistration result polling, mirroring the web UI cadence
_POLL_INTERVAL = 0.5
_POLL_ATTEMPTS = 6


@dataclass(eq=False, repr=False, kw_only=True)
class ARDdnsAction(ARAction):
    """Mutate the DDNS configuration or trigger a DDNS operation."""

    command: ARDdnsCommand
    state: bool | None = None
    # SET: the config fields to write; other commands ignore it
    config: ARDdnsConfig = field(default_factory=dict)

    def _key(self) -> tuple[Any, ...]:
        """Key by command, state and the config fields."""

        return (self.command, self.state, tuple(sorted(self.config.items())))


def _serialize_str(value: Any) -> str:
    """Serialize a text config value."""

    if isinstance(value, Password):
        return value.value
    return str(value)


def _serialize_bool(value: Any) -> int | None:
    """Serialize a flag config value."""

    flag = raw_to_bool(value)
    return None if flag is None else int(flag)


def _serialize_server(value: Any) -> str | None:
    """Serialize a server config value."""

    server = ARDdnsServer.from_value(value)
    return None if server is ARDdnsServer.UNKNOWN else server.value


# Writable config fields: field -> nvram key, serializer
_WRITE: tuple[tuple[ARDdnsField, ARNvramType, Callable[[Any], Any]], ...] = (
    (ARDdnsField.HOSTNAME, ARNvramType.DDNS_HOSTNAME, _serialize_str),
    (ARDdnsField.IPV6_UPDATE, ARNvramType.DDNS_IPV6_UPDATE, _serialize_bool),
    (ARDdnsField.PASSWORD, ARNvramType.DDNS_PASSWORD, _serialize_str),
    (
        ARDdnsField.REFRESH_INTERVAL,
        ARNvramType.DDNS_REFRESH_INTERVAL,
        raw_to_int,
    ),
    (ARDdnsField.SERVER, ARNvramType.DDNS_SERVER, _serialize_server),
    (ARDdnsField.USERNAME, ARNvramType.DDNS_USERNAME, _serialize_str),
    (
        ARDdnsField.VERIFICATION,
        ARNvramType.DDNS_REGULAR_CHECK,
        _serialize_bool,
    ),
    (
        ARDdnsField.VERIFICATION_PERIOD,
        ARNvramType.DDNS_REGULAR_PERIOD,
        raw_to_int,
    ),
    (ARDdnsField.WAN_UNIT, ARNvramType.DDNS_WAN_UNIT, raw_to_int),
    (ARDdnsField.WILDCARD, ARNvramType.DDNS_WILDCARD, _serialize_bool),
)

# The fields a SET can write; STATE rides along via `action.state`
_WRITABLE: frozenset[ARDdnsField] = frozenset(
    field_ for field_, _, _ in _WRITE
)


async def _fetch_current(
    get_data_callback: ARCallbackType | None,
) -> ARDdnsConfig | None:
    """Read the current DDNS data, or None when it cannot be fetched."""

    if get_data_callback is None:
        return None
    fetched = await get_data_callback(ARDdnsSourceUniversal)
    if not isinstance(fetched, dict):
        return None
    data = fetched.get(ARDdnsSourceUniversal)
    return data if isinstance(data, dict) else None


def _state_arguments(action: ARDdnsAction) -> dict[str, Any] | None:
    """Build the arguments for the master toggle."""

    if action.state is None:
        _LOGGER.debug("STATE rejected: no state given")
        return None
    return {ARNvramType.DDNS_STATE.value: int(action.state)}


async def _config_arguments(
    action: ARDdnsAction,
    get_data_callback: ARCallbackType | None,
) -> dict[str, Any] | None:
    """Build the arguments for a config write."""

    # Surface config the SET cannot apply instead of dropping it silently
    dropped = set(action.config) - _WRITABLE
    if dropped:
        _LOGGER.debug("SET ignores non-writable config fields: %s", dropped)

    arguments: dict[str, Any] = {}
    for field_, key, serialize in _WRITE:
        if field_ not in action.config:
            continue
        value = action.config[field_]
        # No value clears the setting
        serialized = "" if value is None else serialize(value)
        if serialized is None:
            _LOGGER.debug("SET rejected: bad value for %s: %s", field_, value)
            return None
        arguments[key.value] = serialized

    if not arguments and action.state is None:
        _LOGGER.debug("SET rejected: no writable fields given")
        return None

    # The toggle can ride along with a config write
    if action.state is not None:
        arguments[ARNvramType.DDNS_STATE.value] = int(action.state)

    # A hostname change unbinds the registered one, as the web UI does
    hostname = arguments.get(ARNvramType.DDNS_HOSTNAME.value)
    if hostname is not None:
        current = await _fetch_current(get_data_callback)
        if current is not None and current.get(ARDdnsField.HOSTNAME) != (
            hostname
        ):
            arguments[ARNvramType.DDNS_REPLACE_STATUS.value] = 0

    return arguments


def _dispatched(value: Any) -> bool:
    """Whether a raw endpoint call reached the device.

    A raw fetch returns the body (possibly empty) on success and None on
    failure, while async_read collapses a failed request to {} instead.
    """

    return value is not None and value != {}


async def _deregister(
    callback: ARCallbackType,
    get_data_callback: ARCallbackType | None,
    raw_callback: ARCallbackType | None,
) -> bool:
    """Release the registered ASUS DDNS hostname."""

    # A hostname bound to a Router-app account cannot be released here
    current = await _fetch_current(get_data_callback)
    if current is not None and current.get(ARDdnsField.TOKEN_STATE) is True:
        _LOGGER.debug(
            "DEREGISTER rejected: the hostname is bound to an app account"
        )
        return False

    poster = raw_callback or callback
    dispatched = await poster(endpoint=AREndpoint.DDNS_UNREGISTER)
    if not _dispatched(dispatched):
        return False

    # Wait for the device to report the deregistration outcome
    key = ARNvramType.DDNS_REGISTRATION_RESULT
    request = hook_request(key)

    async def probe(**kwargs: Any) -> Any:
        return await callback(endpoint=AREndpoint.FETCH_DATA, request=request)

    def ready(result: Any) -> bool:
        return str(hook_value(result, key) or "").startswith(
            _UNREGISTER_PREFIX
        )

    outcome = await async_poll_until(
        probe, ready, interval=_POLL_INTERVAL, attempts=_POLL_ATTEMPTS
    )
    if outcome is None:
        _LOGGER.debug("DEREGISTER failed: no result from the device")
        return False
    result = hook_value(outcome, key)
    if read_status(result) is not ARDdnsStatus.SUCCESS:
        _LOGGER.debug("DEREGISTER failed: %s", result)
        return False

    # Wipe the released hostname from the device config
    cleaned = await poster(endpoint=AREndpoint.DDNS_CLEAN)
    return _dispatched(cleaned)


async def run_action(
    callback: ARCallbackType,
    action: ARDdnsAction,
    *,
    get_data_callback: ARCallbackType | None = None,
    raw_callback: ARCallbackType | None = None,
    expire_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> ARServiceResult:
    """Apply the DDNS action."""

    # UPDATE and DEREGISTER carry no config; flag any that would be dropped
    if action.command in (ARDdnsCommand.UPDATE, ARDdnsCommand.DEREGISTER) and (
        action.state is not None or action.config
    ):
        _LOGGER.debug("%s ignores state and config", action.command)

    if action.command is ARDdnsCommand.DEREGISTER:
        result = ARServiceResult(
            success=await _deregister(
                callback, get_data_callback, raw_callback
            )
        )
    elif action.command is ARDdnsCommand.UPDATE:
        # The web UI forces an update outside the apply flow
        result = await async_run_service(
            callback,
            ARService.DDNS_CLIENT,
            action_mode=ARActionMode.UPDATE,
            raw_callback=raw_callback,
        )
    else:
        if action.command is ARDdnsCommand.STATE:
            arguments = _state_arguments(action)
        elif action.command is ARDdnsCommand.SET:
            arguments = await _config_arguments(action, get_data_callback)
        else:
            _LOGGER.debug("Unknown DDNS command: %s", action.command)
            return ARServiceResult(success=False)

        if not arguments:
            return ARServiceResult(success=False)

        result = await async_run_service(
            callback,
            ARService.DDNS_RESTART,
            arguments=arguments,
            raw_callback=raw_callback,
        )

    # Drop the now-stale cached config and its per-item nvram values,
    # so the next read refetches from the device
    if result.success and expire_callback is not None:
        await expire_callback(ARDdnsSourceUniversal)
        await async_expire_values(expire_callback, DDNS_REQUEST)

    return result


ARCallReg.register_action(ARDdnsAction, run_action=run_action)


__all__ = [
    "ARDdnsAction",
    "ARDdnsConfig",
    "run_action",
]
