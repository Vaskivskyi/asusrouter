"""Action module."""

from __future__ import annotations

import asyncio
from enum import StrEnum
import logging
from typing import Any

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.types import ARCallbackType

_LOGGER = logging.getLogger(__name__)

# The router needs a moment to spin up a run after the trigger returns;
# reading sooner still sees the previous run and stale/absent results
_RUN_START_DELAY = 1.0


class ARActionType(FromStrMixin, StrEnum):
    """A modification applied to a device list, reusable across modules."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    ADD = "add"
    CLEAN = "clean"
    REMOVE = "remove"


class ARAction:
    """AsusRouter action.

    A universal class representing an action to run on the device.

    Actions are equal by exact type and their `_key()`; router-global
    actions keep the empty default, subclasses with defining parameters
    override `_key` only.
    """

    def __init__(self) -> None:
        """Initialize the action."""

    def _key(self) -> tuple[Any, ...]:
        """Return the defining fields for equality and hashing."""

        return ()

    def __eq__(self, other: object) -> bool:
        """Equal by exact type and defining fields."""

        if type(other) is not type(self):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self) -> int:
        """Hash by type and defining fields."""

        return hash((type(self), *self._key()))

    def __repr__(self) -> str:
        """Representation of the action."""

        return f"<{type(self).__name__}>"


async def async_start_run(
    run_action_callback: ARCallbackType | None,
    action: ARAction,
    *,
    delay: float = _RUN_START_DELAY,
) -> bool:
    """Trigger an action run and give the device time to start it."""

    if run_action_callback is None:
        return False
    if not await run_action_callback(action):
        _LOGGER.debug("%r did not start; dropping results", action)
        return False
    await asyncio.sleep(delay)
    return True


__all__ = [
    "ARAction",
    "ARActionType",
    "async_start_run",
]
