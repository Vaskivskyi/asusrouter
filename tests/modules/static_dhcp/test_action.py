"""Tests for static DHCP actions."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.service.action import ARServiceResult
from asusrouter.modules.static_dhcp import (
    STATIC_DHCP_REQUEST,
    ARStaticDHCPAction,
    ARStaticDHCPCommand,
    ARStaticDHCPField,
    ARStaticDHCPLayout,
    ARStaticDHCPSourceUniversal,
    StaticDHCPLease,
    run_action,
)


def _poster(service: str = "restart_dnsmasq") -> AsyncMock:
    """Build a router push callback."""

    return AsyncMock(return_value={"run_service": service})


def _data(
    *,
    state: bool,
    leases: list[StaticDHCPLease],
    complete: bool = True,
) -> AsyncMock:
    """Build a source callback for an authoritative snapshot."""

    return AsyncMock(
        return_value={
            ARStaticDHCPSourceUniversal: {
                ARStaticDHCPField.COMPLETE: complete,
                ARStaticDHCPField.LEASES: leases,
                ARStaticDHCPField.STATE: state,
            }
        }
    )


def _payload(callback: AsyncMock) -> dict[str, object]:
    """Decode the request body pushed to the router."""

    assert callback.await_args.kwargs["endpoint"] is AREndpoint.PUSH_DATA
    return json.loads(callback.await_args.kwargs["request"])


async def test_add_preserves_disabled_legacy_reservations() -> None:
    """ADD includes saved disabled rows and retains old firmware layout."""

    current = [
        StaticDHCPLease(
            mac="AA:BB:CC:DD:EE:FF",
            ip="192.168.1.2",
            hostname="printer",
            layout=ARStaticDHCPLayout.LEGACY,
        )
    ]
    callback = _poster()
    action = ARStaticDHCPAction(
        command=ARStaticDHCPCommand.ADD,
        leases=[
            StaticDHCPLease(
                mac="11:22:33:44:55:66",
                ip="192.168.1.3",
                hostname="scanner",
            )
        ],
    )

    result = await run_action(
        callback,
        action,
        fetch_data_callback=_data(state=False, leases=current),
    )

    payload = _payload(callback)
    assert payload["dhcp_static_x"] == 1
    assert payload["dhcp_staticlist"] == (
        "<AA:BB:CC:DD:EE:FF>192.168.1.2>printer"
        "<11:22:33:44:55:66>192.168.1.3>scanner"
    )
    assert result.success is True


async def test_incomplete_snapshot_blocks_add() -> None:
    """ADD fails closed if the current list was not read completely."""

    callback = _poster()
    result = await run_action(
        callback,
        ARStaticDHCPAction(
            command=ARStaticDHCPCommand.ADD,
            leases=[
                StaticDHCPLease(
                    mac="AA:BB:CC:DD:EE:FF",
                    ip="192.168.1.2",
                )
            ],
        ),
        fetch_data_callback=_data(state=True, leases=[], complete=False),
    )

    assert result.success is False
    callback.assert_not_awaited()


async def test_remove_reports_failed_apply() -> None:
    """A failed dnsmasq apply is returned as failure, not desired data."""

    callback = _poster("restart_firewall")
    result = await run_action(
        callback,
        ARStaticDHCPAction(
            command=ARStaticDHCPCommand.REMOVE,
            macs=["AA:BB:CC:DD:EE:FF"],
        ),
        fetch_data_callback=_data(
            state=True,
            leases=[
                StaticDHCPLease(
                    mac="AA:BB:CC:DD:EE:FF",
                    ip="192.168.1.2",
                )
            ],
        ),
    )

    assert isinstance(result, ARServiceResult)
    assert result.success is False


async def test_remove_last_lease_disables_static_dhcp() -> None:
    """Removing the final enabled reservation clears and disables the list."""

    callback = _poster()
    result = await run_action(
        callback,
        ARStaticDHCPAction(
            command=ARStaticDHCPCommand.REMOVE,
            macs=["AA:BB:CC:DD:EE:FF"],
        ),
        fetch_data_callback=_data(
            state=True,
            leases=[
                StaticDHCPLease(
                    mac="AA:BB:CC:DD:EE:FF",
                    ip="192.168.1.2",
                )
            ],
        ),
    )

    payload = _payload(callback)
    assert payload["dhcp_staticlist"] == ""
    assert payload["dhcp_static_x"] == 0
    assert result.success is True


async def test_remove_missing_lease_is_successful_noop() -> None:
    """Removing an absent MAC does not restart dnsmasq."""

    callback = _poster()
    result = await run_action(
        callback,
        ARStaticDHCPAction(
            command=ARStaticDHCPCommand.REMOVE,
            macs=["11:22:33:44:55:66"],
        ),
        fetch_data_callback=_data(
            state=True,
            leases=[
                StaticDHCPLease(
                    mac="AA:BB:CC:DD:EE:FF",
                    ip="192.168.1.2",
                )
            ],
        ),
    )

    assert result.success is True
    callback.assert_not_awaited()


async def test_success_expires_source_and_nvram() -> None:
    """A successful write expires all three related cache entries."""

    expire = AsyncMock()
    result = await run_action(
        _poster(),
        ARStaticDHCPAction(
            command=ARStaticDHCPCommand.STATE,
            state=False,
        ),
        expire_callback=expire,
    )

    assert result.success is True
    assert [call.args[0] for call in expire.await_args_list] == [
        ARStaticDHCPSourceUniversal,
        *STATIC_DHCP_REQUEST,
    ]
