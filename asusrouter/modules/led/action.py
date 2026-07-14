"""LED action for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from asusrouter.modules.action import ARAction
from asusrouter.modules.common.command import ARService
from asusrouter.modules.led.enums import ARLedField
from asusrouter.modules.led.source import LED_REQUEST, ARLedSourceUniversal
from asusrouter.modules.nvram import ARNvramType, async_expire_values
from asusrouter.modules.service.action import (
    ARServiceResult,
    async_run_service,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.poll import async_poll_until
from asusrouter.tools.types import ARCallbackType

_LOGGER = logging.getLogger(__name__)

# start_ctrl_led restarts the LED daemon; nvram led_val reads blank for a
# moment, so poll it until it settles back to a real on/off value
_POLL_INTERVAL = 0.5
_POLL_ATTEMPTS = 6


@dataclass(eq=False, repr=False, kw_only=True)
class ARLedAction(ARAction):
    """Turn the device LED on or off."""

    state: bool

    def _key(self) -> tuple[Any, ...]:
        """Key by the target state."""

        return (self.state,)


async def _async_wait_settled(get_data_callback: ARCallbackType) -> bool:
    """Poll the LED state until it settles to a real on/off value."""

    async def probe(**kwargs: Any) -> Any:
        return await get_data_callback(ARLedSourceUniversal)

    def ready(result: Any) -> bool:
        if not isinstance(result, dict):
            return False
        data = result.get(ARLedSourceUniversal)
        return (
            isinstance(data, dict) and data.get(ARLedField.STATE) is not None
        )

    settled = await async_poll_until(
        probe, ready, interval=_POLL_INTERVAL, attempts=_POLL_ATTEMPTS
    )
    return settled is not None


async def run_action(
    callback: ARCallbackType,
    action: ARLedAction,
    *,
    get_data_callback: ARCallbackType | None = None,
    expire_callback: ARCallbackType | None = None,
    raw_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> ARServiceResult:
    """Apply the LED action."""

    arguments = {ARNvramType.LED.value: int(action.state)}
    result = await async_run_service(
        callback,
        ARService.LED_CONTROL,
        arguments=arguments,
        raw_callback=raw_callback,
    )

    if not result.success:
        return result

    # Wait until state is settled
    if get_data_callback is not None:
        if not await _async_wait_settled(get_data_callback):
            _LOGGER.debug("LED state did not settle after the switch")
    elif expire_callback is not None:
        # Without a data callback, drop the stale cache for the next read
        await expire_callback(ARLedSourceUniversal)
        await async_expire_values(expire_callback, LED_REQUEST)

    return result


ARCallReg.register_action(ARLedAction, run_action=run_action)


__all__ = [
    "ARLedAction",
    "run_action",
]
