"""LED action for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any

from asusrouter.modules.action import ARAction
from asusrouter.modules.common.command import ARService
from asusrouter.modules.firmware import AR_FW_MERLIN_LIKE
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

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity

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


async def async_recover_state(
    run_action_callback: ARCallbackType,
    desired: bool | None,
    *,
    identity: ARDeviceIdentity | None = None,
) -> bool:
    """Reassert a user-set LED off-state after a reboot.

    Merlin-like firmware turns the LED back on at boot, so an off-state is
    lost on reboot. Only an off-state needs recovery, and only there: the
    fix is a quick on/off toggle, which is what re-applies the off-state.
    """

    if desired is not False:
        return False

    firmware_type = identity.firmware.firmware_type if identity else None
    if firmware_type not in AR_FW_MERLIN_LIKE:
        return False

    _LOGGER.debug("Recovering the LED off-state after a reboot")
    await run_action_callback(ARLedAction(state=True))
    await run_action_callback(ARLedAction(state=False))
    return True


ARCallReg.register_action(ARLedAction, run_action=run_action)


__all__ = [
    "ARLedAction",
    "async_recover_state",
    "run_action",
]
