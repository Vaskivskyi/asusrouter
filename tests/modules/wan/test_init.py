"""Tests for the WAN module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.const import AR_CALL_FETCH_STATE
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
    ARDualWanMode,
    ARWan,
    ARWanSource,
    ARWanSourceUniversal,
    ARWanUnit,
    fetch_state,
    translate_state,
)
from asusrouter.modules.wan.source import _WAN_REQUEST, _parse_lb_ratio
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.identifiers import IpAddress, MacAddress

_MAC = MacAddress.from_value("AA:BB:CC:DD:EE:FF")


def _idx(kind: ARNvramIndexType, index: int) -> ARNvramIndexSource:
    """Build an indexed source key for the values dict."""

    return ARNvramIndexSource(kind, index)


def _full_values() -> dict[Any, Any]:
    """Build a translated values dict for a fully populated unit 0."""

    return {
        # Globals
        ARNvramType.WAN_UNIT: 0,
        ARNvramType.LINK_INTERNET: ARConnectionStatus.CONNECTED,
        ARNvramType.LINK_WAN0: True,
        ARNvramType.DUAL_WAN_MODE: "lb",
        ARNvramType.DUAL_WAN_CONFIG: ["lan", "usb"],
        ARNvramType.DUAL_WAN_CAPABILITY: ["wan", "usb", "lan"],
        ARNvramType.DUAL_WAN_LANPORT: 5,
        ARNvramType.DUAL_WAN_LB_RATIO: "9:1",
        ARNvramType.DUAL_WAN_STANDBY: False,
        ARNvramType.DUAL_WAN_ROUTING: False,
        ARNvramType.DUAL_WAN_USB_BACKUP: False,
        ARNvramType.DUAL_WAN_EXTWAN: False,
        ARNvramType.WAN_AUTODETECT: False,
        ARNvramType.WAN_AGGREGATION: True,
        ARNvramType.WAN_AGGREGATION_PORTS: ["1", "2"],
        ARNvramType.WAN_S46_AFTR: IpAddress.from_value("2001:db8::1"),
        ARNvramType.WAN_S46_B4ADDR: IpAddress.from_value("192.0.0.2"),
        ARNvramType.WATCHDOG_ENABLE: True,
        ARNvramType.WATCHDOG_TARGET: "8.8.8.8",
        ARNvramType.WATCHDOG_INTERVAL: 3,
        ARNvramType.WATCHDOG_MAX_FAIL: 2,
        ARNvramType.WATCHDOG_FAILBACK_COUNT: 1,
        # Unit 0 status
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
        # Unit 0 addresses
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
        # Unit 0 config
        _idx(ARNvramIndexType.WAN_MTU, 0): 1492,
        _idx(ARNvramIndexType.WAN_NAT, 0): True,
        _idx(ARNvramIndexType.WAN_DHCP_ENABLE, 0): True,
        _idx(ARNvramIndexType.WAN_DNS_ENABLE, 0): True,
        _idx(ARNvramIndexType.WAN_DNS1, 0): IpAddress.from_value("1.1.1.1"),
        _idx(ARNvramIndexType.WAN_DNS2, 0): IpAddress.from_value("1.0.0.1"),
        _idx(ARNvramIndexType.WAN_HOSTNAME, 0): "router",
        _idx(ARNvramIndexType.WAN_CLIENTID, 0): "cid",
        _idx(ARNvramIndexType.WAN_VENDORID, 0): "vid",
        _idx(ARNvramIndexType.WAN_MAC_CLONE, 0): _MAC,
        _idx(ARNvramIndexType.WAN_DOT1Q, 0): True,
        _idx(ARNvramIndexType.WAN_VID, 0): 10,
        _idx(ARNvramIndexType.WAN_ROUTING_ISP, 0): "isp",
        _idx(ARNvramIndexType.WAN_ROUTING_ISP_ENABLE, 0): True,
        _idx(ARNvramIndexType.WAN_ISP_COUNTRY, 0): "US",
        _idx(ARNvramIndexType.WAN_ISP_LIST, 0): "list",
        _idx(ARNvramIndexType.WAN_ISP_NUM, 0): "1",
        # Unit 0 PPP
        _idx(ARNvramIndexType.WAN_PPP_ECHO, 0): 1,
        _idx(ARNvramIndexType.WAN_PPP_ECHO_INTERVAL, 0): 6,
        _idx(ARNvramIndexType.WAN_PPP_ECHO_FAILURE, 0): 10,
        _idx(ARNvramIndexType.WAN_PPP_CONN, 0): "conn",
        _idx(ARNvramIndexType.WAN_HEARTBEAT, 0): "host",
        _idx(ARNvramIndexType.WAN_PPPOE_AC, 0): "ac",
        _idx(ARNvramIndexType.WAN_PPPOE_HOSTUNIQ, 0): "uniq",
        _idx(ARNvramIndexType.WAN_PPPOE_IDLETIME, 0): 0,
        _idx(ARNvramIndexType.WAN_PPPOE_MRU, 0): 1492,
        _idx(ARNvramIndexType.WAN_PPPOE_MTU, 0): 1492,
        _idx(ARNvramIndexType.WAN_PPPOE_OPTIONS, 0): "opts",
        _idx(ARNvramIndexType.WAN_PPPOE_SERVICE, 0): "svc",
        # Unit 0 softwire
        _idx(ARNvramIndexType.WAN_S46_DSLITE_MODE, 0): 1,
        _idx(ARNvramIndexType.WAN_S46_DSLITE_SVC, 0): "transix",
        _idx(ARNvramIndexType.WAN_S46_EALEN, 0): 8,
        _idx(ARNvramIndexType.WAN_S46_OFFSET, 0): 6,
        _idx(ARNvramIndexType.WAN_S46_PEER, 0): IpAddress.from_value(
            "2001:db8::2"
        ),
        _idx(ARNvramIndexType.WAN_S46_PREFIX4, 0): IpAddress.from_value(
            "192.0.2.0"
        ),
        _idx(ARNvramIndexType.WAN_S46_PREFIX4LEN, 0): 24,
        _idx(ARNvramIndexType.WAN_S46_PREFIX6, 0): IpAddress.from_value(
            "2001:db8::"
        ),
        _idx(ARNvramIndexType.WAN_S46_PREFIX6LEN, 0): 64,
        _idx(ARNvramIndexType.WAN_S46_PSID, 0): 3,
        _idx(ARNvramIndexType.WAN_S46_PSIDLEN, 0): 4,
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

    assert ARNvramType.DUAL_WAN_MODE in request
    assert ARNvramType.WAN_UNIT in request
    assert _idx(ARNvramIndexType.WAN_MTU, 0) in request
    assert _idx(ARNvramIndexType.WAN_MTU, 1) in request
    # 23 flat members + 60 indexed members per unit, two units
    assert len(request) == 23 + 60 * 2


class TestParseLbRatio:
    """Tests for _parse_lb_ratio."""

    def test_valid(self) -> None:
        """A `primary:secondary` string parses to two ints."""

        assert _parse_lb_ratio("9:1") == (9, 1)

    @pytest.mark.parametrize(
        "raw",
        ["", "9", "9:1:2", "a:b"],
        ids=["empty", "single", "too_many", "non_int"],
    )
    def test_invalid(self, raw: str) -> None:
        """Malformed ratios resolve to None."""

        assert _parse_lb_ratio(raw) is None


class TestGetState:
    """Tests for fetch_state."""

    @pytest.mark.asyncio
    async def test_no_data_callback(self) -> None:
        """Without a data callback an empty dict is returned."""

        result = await fetch_state(AsyncMock(), ARWanSourceUniversal)
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_values(self) -> None:
        """The fetched NVRAM dict is returned as-is."""

        values = {ARNvramType.WAN_UNIT: 0}
        fetch_data_callback = AsyncMock(return_value=values)

        result = await fetch_state(
            AsyncMock(),
            ARWanSourceUniversal,
            fetch_data_callback=fetch_data_callback,
        )

        assert result == values
        fetch_data_callback.assert_awaited_once_with(_WAN_REQUEST)

    @pytest.mark.asyncio
    async def test_non_dict_values(self) -> None:
        """A non-dict fetch result degrades to an empty dict."""

        fetch_data_callback = AsyncMock(return_value=None)

        result = await fetch_state(
            AsyncMock(),
            ARWanSourceUniversal,
            fetch_data_callback=fetch_data_callback,
        )

        assert result == {}


class TestTranslateState:
    """Tests for translate_state."""

    def test_non_dict_returns_empty_wan(self) -> None:
        """Non-dict input yields a default ARWan."""

        assert translate_state(None) == ARWan()

    def test_active_unit_and_internet(self) -> None:
        """Active unit and internet status come from the flat keys."""

        wan = translate_state(_full_values())
        assert wan.active_unit == 0
        assert wan.internet_status is ARConnectionStatus.CONNECTED

    def test_full_unit(self) -> None:
        """A fully populated unit 0 is translated end to end."""

        unit = translate_state(_full_values()).units[0]
        assert isinstance(unit, ARWanUnit)

        # Status
        assert unit.enable is True
        assert unit.primary is True
        assert unit.protocol is ARConnectionMethod.PPPOE
        assert unit.status is ARConnectionStatus.CONNECTED
        assert unit.link is True
        assert unit.real_ip == IpAddress.from_value("5.6.7.8")
        assert unit.real_ip_state is True
        # Addresses
        assert unit.main.ip == IpAddress.from_value("1.2.3.4")
        assert unit.main.dns == [IpAddress.from_value("8.8.8.8")]
        assert unit.extra.ip == IpAddress.from_value("9.9.9.9")
        # Config
        assert unit.mtu == 1492
        assert unit.nat is True
        assert unit.dhcp_enable is True
        assert unit.dns_auto is True
        assert unit.dns_servers == [
            IpAddress.from_value("1.1.1.1"),
            IpAddress.from_value("1.0.0.1"),
        ]
        assert unit.hostname == "router"
        assert unit.client_id == "cid"
        assert unit.vendor_id == "vid"
        assert unit.mac_clone == _MAC
        assert unit.routing_isp == "isp"
        assert unit.routing_isp_enable is True
        assert unit.isp_country == "US"
        # VLAN
        assert unit.vlan.tagged is True
        assert unit.vlan.vid == 10
        # PPP
        assert unit.ppp.echo == 1
        assert unit.ppp.pppoe_mtu == 1492
        assert unit.ppp.pppoe_service == "svc"
        # Softwire
        assert unit.softwire.dslite_mode == 1
        assert unit.softwire.aftr == IpAddress.from_value("2001:db8::1")
        assert unit.softwire.b4addr == IpAddress.from_value("192.0.0.2")
        assert unit.softwire.peer == IpAddress.from_value("2001:db8::2")
        assert unit.softwire.prefix4_len == 24
        assert unit.softwire.psid == 3

    def test_empty_unit_defaults(self) -> None:
        """A unit with no values falls back to defaults."""

        unit = translate_state(_full_values()).units[1]
        assert unit.enable is False
        assert unit.protocol is ARConnectionMethod.UNKNOWN
        assert unit.status is ARConnectionStatus.UNKNOWN
        assert unit.link is False
        assert unit.main.ip is None
        assert unit.mtu is None
        assert unit.nat is False
        assert unit.dns_servers == []
        assert unit.mac_clone is None
        assert unit.vlan.tagged is False
        assert unit.softwire.dslite_mode is None

    def test_dualwan_full(self) -> None:
        """The dual WAN block carries all of its config."""

        dualwan = translate_state(_full_values()).dualwan
        assert dualwan is not None
        assert dualwan.mode is ARDualWanMode.LOAD_BALANCE
        assert dualwan.priority == ["lan", "usb"]
        assert dualwan.state is True
        assert dualwan.capability == ["wan", "usb", "lan"]
        assert dualwan.lan_port == 5
        assert dualwan.lb_ratio == (9, 1)

    def test_aggregation_and_watchdog(self) -> None:
        """Aggregation and watchdog blocks are built when reported."""

        wan = translate_state(_full_values())

        assert wan.aggregation is not None
        assert wan.aggregation.state is True
        assert wan.aggregation.ports == ["1", "2"]

        assert wan.watchdog is not None
        assert wan.watchdog.enable is True
        assert wan.watchdog.target == "8.8.8.8"
        assert wan.watchdog.interval == 3

    def test_blocks_none_when_absent(self) -> None:
        """Dual WAN, aggregation and watchdog are None without data."""

        wan = translate_state({})
        assert wan.dualwan is None
        assert wan.aggregation is None
        assert wan.watchdog is None

    def test_dualwan_none_when_priority_empty(self) -> None:
        """A blank dual WAN priority (e.g. single WAN) yields None."""

        wan = translate_state({ARNvramType.DUAL_WAN_CONFIG: [""]})
        assert wan.dualwan is None

    def test_dualwan_inactive_priority(self) -> None:
        """A `none` secondary priority marks dual WAN inactive."""

        wan = translate_state(
            {
                ARNvramType.DUAL_WAN_MODE: "fo",
                ARNvramType.DUAL_WAN_CONFIG: ["wan", "none"],
            }
        )
        assert wan.dualwan is not None
        assert wan.dualwan.state is False


def test_module_registers_source() -> None:
    """The WAN source resolves to the module fetch_state callable."""

    assert (
        ARCallReg.get_callable(ARWanSourceUniversal, AR_CALL_FETCH_STATE)
        is fetch_state
    )
