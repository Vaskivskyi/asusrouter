"""Block-all-devices action for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from asusrouter.modules.action import ARAction
from asusrouter.modules.common.command import ARService
from asusrouter.modules.nvram import async_expire_values
from asusrouter.modules.parental_control.block_all.source import (
    KEY_BLOCK_ALL,
    ARBlockAllSourceUniversal,
)
from asusrouter.modules.service.action import (
    ARServiceResult,
    async_run_service,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.types import ARCallbackType


@dataclass(eq=False, repr=False, kw_only=True)
class ARBlockAllAction(ARAction):
    """Toggle the block-all-devices kill switch."""

    state: bool


async def run_action(
    callback: ARCallbackType,
    action: ARBlockAllAction,
    *,
    raw_callback: ARCallbackType | None = None,
    expire_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> ARServiceResult:
    """Apply the block-all toggle via `restart_firewall`."""

    result = await async_run_service(
        callback,
        ARService.FIREWALL_RESTART,
        arguments={KEY_BLOCK_ALL.value: int(action.state)},
        raw_callback=raw_callback,
    )

    # Drop the now-stale cached switch so the next read refetches
    if result.success and expire_callback is not None:
        await expire_callback(ARBlockAllSourceUniversal)
        await async_expire_values(expire_callback, KEY_BLOCK_ALL)

    return result


ARCallReg.register_action(ARBlockAllAction, run_action=run_action)


__all__ = [
    "ARBlockAllAction",
    "run_action",
]
