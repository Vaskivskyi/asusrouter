"""SpeedTest servers data source for AsusRouter."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.endpoint_v2.hooks import (
    ARHook,
    hook_request,
    hook_value,
)
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.speedtest.models import (
    EXE_TYPE_LIST,
    ARSpeedTestServer,
    build_run_request,
    servers_from_list,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.poll import async_poll_until
from asusrouter.tools.types import ARCallbackType

# The router populates the server list asynchronously after the trigger,
# so poll the hook until it returns a usable list
_MIN_SERVERS = 2
_POLL_INTERVAL = 1.0
_POLL_ATTEMPTS = 15

_SERVERS_REQUEST = hook_request(ARHook.OOKLA_SPEEDTEST_SERVERS)


# Sources and actions


class ARSpeedTestServersSource(ARDataSource):
    """AsusRouter speedtest servers data source."""


# Universal instance - preferred
ARSpeedTestServersSourceUniversal: ARSpeedTestServersSource = (
    ARSpeedTestServersSource()
)


# Fetch


async def _async_fetch(callback: ARCallbackType) -> Any:
    """Fetch the raw server list from the hook."""

    data = await callback(
        endpoint=AREndpoint.FETCH_DATA, request=_SERVERS_REQUEST
    )
    return hook_value(data, ARHook.OOKLA_SPEEDTEST_SERVERS)


async def get_state(
    callback: ARCallbackType,
    source: ARSpeedTestServersSource,
    *,
    refresh: bool = False,
    **kwargs: Any,
) -> Any:
    """Fetch the speedtest server list; with `refresh`, ask for a fresh one."""

    if refresh:
        # Ask the router to rebuild the list, then wait for it to fill
        await callback(
            endpoint=AREndpoint.RUN_SPEEDTEST,
            request=build_run_request(EXE_TYPE_LIST),
        )
        fresh = await async_poll_until(
            lambda **_: _async_fetch(callback),
            lambda value: (
                isinstance(value, list) and len(value) >= _MIN_SERVERS
            ),
            interval=_POLL_INTERVAL,
            attempts=_POLL_ATTEMPTS,
        )
        return fresh if fresh is not None else {}

    servers = await _async_fetch(callback)
    return servers if servers is not None else {}


def translate_state(data: Any, **kwargs: Any) -> list[ARSpeedTestServer]:
    """Translate the raw server list into servers."""

    return servers_from_list(data)


# Registration

ARCallReg.register_module(
    ARSpeedTestServersSource,
    get_state=get_state,
    translate_state=translate_state,
)


__all__ = [
    "ARSpeedTestServersSource",
    "ARSpeedTestServersSourceUniversal",
    "get_state",
    "translate_state",
]
