"""Service action for AsusRouter."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import json
from typing import TYPE_CHECKING, Any

from asusrouter.modules.action import ARAction
from asusrouter.modules.common.command import (
    RC_SERVICE_KEY,
    ARActionMode,
    ARService,
)
from asusrouter.modules.common.status import MODIFY_KEY
from asusrouter.modules.endpoint_v2 import AREndpoint, build_push_request
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters_v2.raw import raw_to_bool, raw_to_int
from asusrouter.tools.types import ARCallbackType

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity

# Response keys of a service run
RUN_SERVICE_KEY = "run_service"
RESTART_NEEDED_TIME_KEY = "restart_needed_time"
ID_KEY = "id"

# Fallback wait (seconds) when the device reports an id but no restart time
_DEFAULT_NEEDED_TIME = 5

# A service, or something coercible into one (a raw string may carry an inline
# argument, e.g. `restart_sdn 3`)
ARServiceInput = ARService | str

# Services that drop the current session by rebooting the device
_REBOOT_SERVICES = {ARService.REBOOT}


def _triggers_reboot(services: list[ARServiceInput]) -> bool:
    """Whether any requested service reboots the device."""

    return any(service in _REBOOT_SERVICES for service in services)


def _as_list(
    services: ARServiceInput | Iterable[ARServiceInput],
) -> list[ARServiceInput]:
    """Coerce a single service or an iterable of them into a list."""

    if isinstance(services, (ARService, str)):
        return [services]
    return list(services)


@dataclass
class ARServiceResult:
    """The outcome of a service run."""

    success: bool
    needed_time: int | None = None
    last_id: int | None = None


class ARServiceAction(ARAction):
    """Run one or more device services via `rc_service`."""

    def __init__(
        self,
        services: ARServiceInput | Iterable[ARServiceInput],
        *,
        arguments: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the action with the service(s) and optional arguments."""

        super().__init__()

        self.services = _as_list(services)
        self.arguments = dict(arguments) if arguments else {}


def build_service_request(
    services: ARServiceInput | Iterable[ARServiceInput],
    *,
    arguments: dict[str, Any] | None = None,
) -> str:
    """Build an applyapp request body that runs one or more services."""

    names = ";".join(str(service) for service in _as_list(services))
    payload: dict[str, Any] = {RC_SERVICE_KEY: names}
    if arguments:
        payload.update(arguments)
    return build_push_request(ARActionMode.APPLY, payload)


def _try_json(text: str) -> dict[str, Any] | None:
    """Parse a JSON object out of a string, or None if it is not one."""

    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def read_service_result(
    result: Any,
    services: ARServiceInput | Iterable[ARServiceInput] | None = None,
) -> ARServiceResult:
    """Read a service-run response into a result."""

    if isinstance(result, str):
        data = _try_json(result)
        if data is None:
            # Non-JSON 200 body: dispatched, but carries no timing details
            return ARServiceResult(success=bool(result.strip()))
    elif isinstance(result, dict):
        data = result
    else:
        return ARServiceResult(success=False)

    needed_time = raw_to_int(data.get(RESTART_NEEDED_TIME_KEY))
    last_id = raw_to_int(data.get(ID_KEY))
    if needed_time is None and last_id is not None:
        needed_time = _DEFAULT_NEEDED_TIME

    ran = data.get(RUN_SERVICE_KEY)
    if ran is not None and services is not None:
        requested = ";".join(str(service) for service in _as_list(services))
        success = str(ran).strip(";") == requested.strip(";")
    elif ran is not None:
        success = bool(str(ran))
    else:
        # A reachable JSON 200 without an echo is dispatched unless the
        # device explicitly reports no modification
        success = raw_to_bool(data.get(MODIFY_KEY)) is not False

    return ARServiceResult(
        success=success, needed_time=needed_time, last_id=last_id
    )


async def async_run_service(
    callback: ARCallbackType,
    services: ARServiceInput | Iterable[ARServiceInput],
    *,
    arguments: dict[str, Any] | None = None,
    raw_callback: ARCallbackType | None = None,
) -> ARServiceResult:
    """Post a service run and read the outcome."""

    request = build_service_request(services, arguments=arguments)
    # Post raw when possible: async_fetch preserves a failed fetch as None,
    # while async_read would collapse it to {} and hide the failure
    poster = raw_callback or callback
    data = await poster(endpoint=AREndpoint.PUSH_DATA, request=request)
    return read_service_result(data, services)


async def run_action(
    callback: ARCallbackType,
    action: ARServiceAction,
    *,
    raw_callback: ARCallbackType | None = None,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> ARServiceResult:
    """Run the action's service(s) and read the outcome."""

    if not action.services:
        return ARServiceResult(success=False)

    result = await async_run_service(
        callback,
        action.services,
        arguments=action.arguments or None,
        raw_callback=raw_callback,
    )

    # A reboot drops the session; flag it so the caller reconnects
    if (
        result.success
        and identity is not None
        and _triggers_reboot(action.services)
    ):
        identity.mark_reboot()

    return result


ARCallReg.register_action(ARServiceAction, run_action=run_action)


__all__ = [
    "ARServiceAction",
    "ARServiceInput",
    "ARServiceResult",
    "async_run_service",
    "build_service_request",
    "read_service_result",
    "run_action",
]
