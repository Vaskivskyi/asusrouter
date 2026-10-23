"""Static DHCP mutation action for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import logging
from typing import Any, ClassVar

from asusrouter.modules.action import ARAction
from asusrouter.modules.common.command import ARService
from asusrouter.modules.nvram import async_expire_values
from asusrouter.modules.service.action import (
    ARServiceResult,
    async_run_service,
)
from asusrouter.modules.static_dhcp.enums import (
    ARStaticDHCPCommand,
    ARStaticDHCPField,
    ARStaticDHCPLayout,
)
from asusrouter.modules.static_dhcp.model import (
    StaticDHCPLease,
    compile_static_dhcp_leases,
    normalize_static_dhcp_lease,
    normalize_static_dhcp_mac,
)
from asusrouter.modules.static_dhcp.source import (
    STATIC_DHCP_REQUEST,
    ARStaticDHCPSourceUniversal,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.types import ARCallbackType

_LOGGER = logging.getLogger(__name__)


@dataclass(eq=False, repr=False, kw_only=True)
class ARStaticDHCPAction(ARAction):
    """Mutate static DHCP reservations or their master toggle."""

    serialized: ClassVar[bool] = True

    command: ARStaticDHCPCommand
    leases: list[StaticDHCPLease] = field(default_factory=list)
    macs: list[str] = field(default_factory=list)
    state: bool | None = None

    def _key(self) -> tuple[Any, ...]:
        """Key by all action parameters."""

        return (
            self.command,
            tuple(self.leases),
            tuple(self.macs),
            self.state,
        )


async def _fetch_current(
    fetch_data_callback: ARCallbackType | None,
) -> tuple[bool, list[StaticDHCPLease]] | None:
    """Read an authoritative lease snapshot or fail closed."""

    if fetch_data_callback is None:
        return None
    fetched = await fetch_data_callback(ARStaticDHCPSourceUniversal)
    if not isinstance(fetched, dict):
        return None
    data = fetched.get(ARStaticDHCPSourceUniversal)
    if (
        not isinstance(data, dict)
        or data.get(ARStaticDHCPField.COMPLETE) is not True
        or not isinstance(data.get(ARStaticDHCPField.STATE), bool)
        or not isinstance(data.get(ARStaticDHCPField.LEASES), list)
    ):
        return None
    return (
        data[ARStaticDHCPField.STATE],
        list(data[ARStaticDHCPField.LEASES]),
    )


def _layout_for_new(
    lease: StaticDHCPLease,
    current: list[StaticDHCPLease],
) -> StaticDHCPLease:
    """Use an existing row's layout, or the list's legacy layout."""

    for saved in current:
        if normalize_static_dhcp_mac(saved.mac) == lease.mac:
            return replace(lease, layout=saved.layout)

    if any(saved.layout is ARStaticDHCPLayout.LEGACY for saved in current):
        return replace(lease, layout=ARStaticDHCPLayout.LEGACY)
    return lease


def _add_arguments(
    action: ARStaticDHCPAction,
    current: list[StaticDHCPLease],
) -> dict[str, str | int] | None:
    """Build an upsert that preserves every unrelated saved row."""

    if not action.leases:
        return None
    additions = [
        _layout_for_new(normalize_static_dhcp_lease(lease), current)
        for lease in action.leases
    ]
    added_macs = {lease.mac for lease in additions}
    final = [
        lease
        for lease in current
        if normalize_static_dhcp_mac(lease.mac) not in added_macs
    ]
    final.extend(additions)
    return compile_static_dhcp_leases(final, enabled=True)


def _remove_arguments(
    action: ARStaticDHCPAction,
    current_state: bool,
    current: list[StaticDHCPLease],
) -> dict[str, str | int] | None:
    """Build a removal that preserves state unless the list becomes empty."""

    if not action.macs:
        return None
    removals = {normalize_static_dhcp_mac(mac) for mac in action.macs}
    final = [
        lease
        for lease in current
        if normalize_static_dhcp_mac(lease.mac) not in removals
    ]
    if len(final) == len(current):
        return {}
    return compile_static_dhcp_leases(
        final,
        enabled=current_state and bool(final),
    )


async def _mutation_arguments(
    action: ARStaticDHCPAction,
    fetch_data_callback: ARCallbackType | None,
) -> dict[str, str | int] | None:
    """Build arguments for an ADD or REMOVE from a fresh snapshot."""

    current_result = await _fetch_current(fetch_data_callback)
    if current_result is None:
        return None
    current_state, current = current_result
    if action.command is ARStaticDHCPCommand.ADD:
        return _add_arguments(action, current)
    if action.command is ARStaticDHCPCommand.REMOVE:
        return _remove_arguments(action, current_state, current)
    return None


async def _arguments(
    action: ARStaticDHCPAction,
    fetch_data_callback: ARCallbackType | None,
) -> dict[str, str | int] | None:
    """Build safe mutation arguments."""

    if action.command is ARStaticDHCPCommand.STATE:
        return (
            None
            if action.state is None
            else {"dhcp_static_x": int(action.state)}
        )
    if action.command is ARStaticDHCPCommand.SET:
        final = [normalize_static_dhcp_lease(lease) for lease in action.leases]
        return compile_static_dhcp_leases(final, enabled=action.state)
    if action.command in (
        ARStaticDHCPCommand.ADD,
        ARStaticDHCPCommand.REMOVE,
    ):
        return await _mutation_arguments(action, fetch_data_callback)
    return None


async def run_action(
    callback: ARCallbackType,
    action: ARStaticDHCPAction,
    *,
    fetch_data_callback: ARCallbackType | None = None,
    fetch_raw_callback: ARCallbackType | None = None,
    expire_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> ARServiceResult:
    """Apply a static DHCP action through dnsmasq restart."""

    try:
        arguments = await _arguments(action, fetch_data_callback)
    except (TypeError, ValueError) as ex:
        _LOGGER.debug("Static DHCP action rejected: %s", ex)
        return ARServiceResult(success=False)

    if arguments is None:
        return ARServiceResult(success=False)
    if not arguments:
        return ARServiceResult(success=True)

    result = await async_run_service(
        callback,
        ARService.DNS_RESTART,
        arguments=arguments,
        fetch_raw_callback=fetch_raw_callback,
    )

    if result.success:
        if expire_callback is not None:
            await expire_callback(ARStaticDHCPSourceUniversal)
        await async_expire_values(expire_callback, STATIC_DHCP_REQUEST)

    return result


ARCallReg.register_action(ARStaticDHCPAction, run_action=run_action)


__all__ = [
    "ARStaticDHCPAction",
    "run_action",
]
