"""Tests for the WAN module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.const import AR_CALL_GET_STATE
from asusrouter.modules.common.connection import (
    ARConnectionMethod,
    ARConnectionStatus,
)
from asusrouter.modules.nvram import (
    ARNvramIndexSource,
    ARNvramIndexType,
    ARNvramType,
)
from asusrouter.modules.wan import (
    _WAN_REQUEST,
    ARDualWanMode,
    ARWan,
    ARWanSource,
    ARWanSourceUniversal,
    ARWanUnit,
    get_state,
    translate_state,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.identifiers import IpAddress


def _idx(kind: ARNvramIndexType, index: int) -> ARNvramIndexSource:
    """Build an indexed source key for the values dict."""

    return ARNvramIndexSource(kind, index)


def _unit0_values() -> dict[Any, Any]:
    """Build a translated values dict for a fully populated unit 0."""

    return {
        ARNvramType.LINK_INTERNET: ARConnectionStatus.CONNECTED,
        ARNvramType.LINK_WAN0: True,
        ARNvramType.DUAL_WAN_MODE: "lb",
        ARNvramType.DUAL_WAN_CONFIG: ["lan", "usb"],
        ARNvramType.WAN_AGGREGATION: True,
        ARNvramType.WAN_AGGREGATION_PORTS: ["1", "2"],
        _idx(ARNvramIndexType.WAN_ENABLE, 0): True,
        _idx(ARNvramIndexType.WAN_PRIMARY, 0): True,
        _idx(ARNvramIndexType.WAN_PROTO, 0): ARConnectionMethod.PPPOE,
        _idx(ARNvramIndexType.WAN_STATE, 0): ARConnectionStatus.CONNECTED,
        _idx(ARNvramIndexType.WAN_STATE_SUB, 0): (
            ARConnectionStatus.DISCONNECTED
        ),
        _idx(ARNvramIndexType.WAN_STATE_AUX, 0): (
            ARConnectionStatus.DISCONNECTED
        ),
        _idx(ARNvramIndexType.WAN_REALIP, 0): IpAddress.from_value("5.6.7.8"),
        _idx(ARNvramIndexType.WAN_REALIP_STATE, 0): True,
        _idx(ARNvramIndexType.WAN_IPADDR, 0): IpAddress.from_value("1.2.3.4"),
        _idx(ARNvramIndexType.WAN_GATEWAY, 0): IpAddress.from_value("1.2.3.1"),
        _idx(ARNvramIndexType.WAN_NETMASK, 0): IpAddress.from_value(
            "255.255.255.0"
        ),
        _idx(ARNvramIndexType.WAN_DNS, 0): [IpAddress.from_value("8.8.8.8")],
        _idx(ARNvramIndexType.WAN_LEASE, 0): 3600,
        _idx(ARNvramIndexType.WAN_EXPIRES, 0): 100,
        _idx(ARNvramIndexType.WAN_IPADDR_X, 0): IpAddress.from_value(
            "9.9.9.9"
        ),
    }


class TestARDualWanMode:
    """Tests for ARDualWanMode."""

    def test_values(self) -> None:
        """Members map to their router codes."""

        assert ARDualWanMode.FAILOVER.value == "fo"
        assert ARDualWanMode.FALLBACK.value == "fb"
        assert ARDualWanMode.LOAD_BALANCE.value == "lb"

    def test_from_value_unknown(self) -> None:
        """Unknown input resolves to UNKNOWN."""

        assert ARDualWanMode.from_value("zz") is ARDualWanMode.UNKNOWN


class TestARWanSource:
    """Tests for ARWanSource."""

    def test_equality_and_hash(self) -> None:
        """All WAN sources are equal and share a hash."""

        assert ARWanSource() == ARWanSource()
        assert hash(ARWanSource()) == hash(ARWanSourceUniversal)

    def test_equality_other_type(self) -> None:
        """Comparison with a non-source returns NotImplemented / False."""

        assert ARWanSource().__eq__("x") is NotImplemented
        assert (ARWanSource() == "x") is False

    def test_repr(self) -> None:
        """The repr is stable."""

        assert repr(ARWanSource()) == "<ARWanSource>"


def test_wan_request() -> None:
    """The request covers the flat members and per-unit indexed sources."""

    request = _WAN_REQUEST

    assert ARNvramType.LINK_INTERNET in request
    assert _idx(ARNvramIndexType.WAN_IPADDR, 0) in request
    assert _idx(ARNvramIndexType.WAN_IPADDR, 1) in request
    # 7 flat members + 20 indexed members per unit, two units
    assert len(request) == 7 + 20 * 2


class TestGetState:
    """Tests for get_state."""

    @pytest.mark.asyncio
    async def test_no_data_callback(self) -> None:
        """Without a data callback an empty dict is returned."""

        result = await get_state(AsyncMock(), ARWanSourceUniversal)
        assert result == {}

    @pytest.mark.asyncio
    async def test_combines_values_and_unit(self) -> None:
        """The NVRAM values and active unit are combined."""

        values = {ARNvramType.LINK_INTERNET: ARConnectionStatus.CONNECTED}
        get_data_callback = AsyncMock(return_value=values)
        callback = AsyncMock(return_value={"get_wan_unit": 1})

        result = await get_state(
            callback,
            ARWanSourceUniversal,
            get_data_callback=get_data_callback,
        )

        assert result == {"values": values, "active_unit": 1}
        get_data_callback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_non_dict_unit_and_values(self) -> None:
        """Non-dict unit and values degrade gracefully."""

        get_data_callback = AsyncMock(return_value=None)
        callback = AsyncMock(return_value=None)

        result = await get_state(
            callback,
            ARWanSourceUniversal,
            get_data_callback=get_data_callback,
        )

        assert result == {"values": {}, "active_unit": None}


class TestTranslateState:
    """Tests for translate_state."""

    def test_non_dict_returns_empty_wan(self) -> None:
        """Non-dict input yields a default ARWan."""

        assert translate_state(None) == ARWan()

    def test_full_unit(self) -> None:
        """A fully populated unit 0 is translated end to end."""

        wan = translate_state({"values": _unit0_values(), "active_unit": 0})

        assert wan.active_unit == 0
        assert wan.internet_status is ARConnectionStatus.CONNECTED

        unit = wan.units[0]
        assert isinstance(unit, ARWanUnit)
        assert unit.enable is True
        assert unit.primary is True
        assert unit.protocol is ARConnectionMethod.PPPOE
        assert unit.status is ARConnectionStatus.CONNECTED
        assert unit.status_sub is ARConnectionStatus.DISCONNECTED
        assert unit.link is True
        assert unit.real_ip == IpAddress.from_value("5.6.7.8")
        assert unit.real_ip_state is True
        assert unit.main.ip == IpAddress.from_value("1.2.3.4")
        assert unit.main.gateway == IpAddress.from_value("1.2.3.1")
        assert unit.main.dns == [IpAddress.from_value("8.8.8.8")]
        assert unit.main.lease == 3600
        assert unit.main.expires == 100
        assert unit.extra.ip == IpAddress.from_value("9.9.9.9")
        assert unit.extra.gateway is None

    def test_empty_unit_defaults(self) -> None:
        """A unit with no values falls back to defaults."""

        wan = translate_state({"values": _unit0_values(), "active_unit": 0})

        unit = wan.units[1]
        assert unit.enable is False
        assert unit.protocol is ARConnectionMethod.UNKNOWN
        assert unit.status is ARConnectionStatus.UNKNOWN
        assert unit.link is False
        assert unit.main.ip is None
        assert unit.main.dns == []

    def test_dualwan_and_aggregation(self) -> None:
        """Dual WAN and aggregation blocks are built when reported."""

        wan = translate_state({"values": _unit0_values(), "active_unit": 0})

        assert wan.dualwan is not None
        assert wan.dualwan.mode is ARDualWanMode.LOAD_BALANCE
        assert wan.dualwan.priority == ["lan", "usb"]
        assert wan.dualwan.state is True

        assert wan.aggregation is not None
        assert wan.aggregation.state is True
        assert wan.aggregation.ports == ["1", "2"]

    def test_dualwan_none_when_absent(self) -> None:
        """No dual WAN data yields None."""

        wan = translate_state({"values": {}, "active_unit": None})
        assert wan.dualwan is None
        assert wan.aggregation is None

    def test_dualwan_none_when_priority_empty(self) -> None:
        """A blank dual WAN priority (e.g. single WAN) yields None."""

        values = {ARNvramType.DUAL_WAN_CONFIG: [""]}
        wan = translate_state({"values": values, "active_unit": None})
        assert wan.dualwan is None

    def test_dualwan_inactive_priority(self) -> None:
        """A `none` secondary priority marks dual WAN inactive."""

        values = {
            ARNvramType.DUAL_WAN_MODE: "fo",
            ARNvramType.DUAL_WAN_CONFIG: ["wan", "none"],
        }
        wan = translate_state({"values": values, "active_unit": None})

        assert wan.dualwan is not None
        assert wan.dualwan.state is False


def test_module_registers_source() -> None:
    """The WAN source resolves to the module get_state callable."""

    assert (
        ARCallReg.get_callable(ARWanSourceUniversal, AR_CALL_GET_STATE)
        is get_state
    )
