"""Tests for the kernel event translation."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.kernel import PATTERNS, AREventKernel
from asusrouter.tools.identifiers import MacAddress
from tests.modules.log.translate import IDENTIFIER, classified, unread

_KEY = AREventKey
_CLIENT = "aa:bb:cc:00:00:01"
_PORT = "eth3 (Int switch port: 10) (Logical Port: 10) (phyId: 1b)"
_DOWN = f"{_PORT} Link DOWN."
_UP = f"{_PORT} Link Up at 100 mbps full duplex AN: On"


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw kernel message."""

    return PATTERNS.translate(content)


class TestBridge:
    """Bridge STP message translation."""

    def test_port_state(self) -> None:
        """A port state message parses bridge, port, interface and state."""

        content = "br0: port 4(wl0.1) entering disabled state"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventKernel.BRIDGE_PORT_STATE,
            _KEY.RAW: content,
            _KEY.BRIDGE: "br0",
            _KEY.PORT: 4,
            _KEY.INTERFACE: "wl0.1",
            _KEY.STATE: "disabled",
        }

    @pytest.mark.parametrize("state", ["listening", "learning", "forwarding"])
    def test_state_variants(self, state: str) -> None:
        """Every STP state word is carried through verbatim."""

        content = f"br0: port 1(vlan1) entering {state} state"

        assert _translate(content)[_KEY.STATE] == state

    def test_topology_change(self) -> None:
        """The topology-change message keeps only the bridge name."""

        content = "br0: topology change detected, propagating"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventKernel.BRIDGE_TOPOLOGY_CHANGE,
            _KEY.RAW: content,
            _KEY.BRIDGE: "br0",
        }


class TestEthernetLink:
    """Ethernet port link state translation."""

    def test_down(self) -> None:
        """Link down carries only the port identity, no speed."""

        assert _translate(_DOWN) == {
            _KEY.EVENT_TYPE: AREventKernel.ETHERNET_LINK_DOWN,
            _KEY.RAW: _DOWN,
            _KEY.INTERFACE: "eth3",
            _KEY.SWITCH_PORT: 10,
            _KEY.LOGICAL_PORT: 10,
            _KEY.PHY_ID: "1b",
        }

    def test_up_with_autoneg(self) -> None:
        """Link up parses speed, duplex and the autonegotiation flag."""

        assert _translate(_UP) == {
            _KEY.EVENT_TYPE: AREventKernel.ETHERNET_LINK_UP,
            _KEY.RAW: _UP,
            _KEY.INTERFACE: "eth3",
            _KEY.SWITCH_PORT: 10,
            _KEY.LOGICAL_PORT: 10,
            _KEY.PHY_ID: "1b",
            _KEY.SPEED: 100,
            _KEY.DUPLEX: "full",
            _KEY.AUTONEG: True,
        }

    def test_up_without_autoneg(self) -> None:
        """Old firmware omits the AN clause, so no autoneg key."""

        content = (
            "eth0 (Int switch port: 3) (Logical Port: 3) (phyId: c) "
            "Link UP at 1000 mbps full duplex"
        )

        event = _translate(content)

        assert event[_KEY.SPEED] == 1000
        assert _KEY.AUTONEG not in event


class TestDriver:
    """Driver banner and init message translation."""

    def test_klogd_start(self) -> None:
        """The BusyBox version is extracted."""

        content = "klogd started: BusyBox v1.25.1 (2018-04-08 14:04:33 EDT)"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventKernel.KLOGD_START,
            _KEY.RAW: content,
            _KEY.VERSION: "1.25.1",
        }

    def test_phy_cal_init(self) -> None:
        """The stub marker maps to PHY_CAL_INIT, no data keys."""

        content = "wlc_phy_cal_init_acphy: NOT Implemented"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventKernel.PHY_CAL_INIT,
            _KEY.RAW: content,
        }

    def test_tasklet_kill_attempt(self) -> None:
        """The warning maps to TASKLET_KILL_ATTEMPT, no data keys."""

        content = "Attempt to kill tasklet from interrupt"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventKernel.TASKLET_KILL_ATTEMPT,
            _KEY.RAW: content,
        }

    def test_wireless_controller(self) -> None:
        """Interface, chip, version and revision are extracted."""

        content = (
            "eth1: Broadcom BCM4331 802.11 Wireless Controller "
            "6.30.163.2002 (r382208)"
        )

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventKernel.WIRELESS_CONTROLLER,
            _KEY.RAW: content,
            _KEY.INTERFACE: "eth1",
            _KEY.CHIP: "BCM4331",
            _KEY.VERSION: "6.30.163.2002",
            _KEY.REVISION: 382208,
        }

    def test_wl_module_init(self) -> None:
        """The parameter name and its hex value are extracted."""

        content = "wl_module_init: passivemode set to 0x1"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventKernel.WL_MODULE_INIT,
            _KEY.RAW: content,
            _KEY.PARAMETER: "passivemode",
            _KEY.VALUE: 1,
        }


class TestPromiscuousMode:
    """Promiscuous mode translation (both message shapes)."""

    def test_entered(self) -> None:
        """`entered` maps to enabled True."""

        content = "device wl0.1 entered promiscuous mode"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventKernel.PROMISCUOUS_MODE,
            _KEY.RAW: content,
            _KEY.INTERFACE: "wl0.1",
            _KEY.ENABLED: True,
        }

    def test_left(self) -> None:
        """`left` maps to enabled False."""

        content = "device eth1 left promiscuous mode"

        assert _translate(content)[_KEY.ENABLED] is False

    def test_set_promiscuity_on(self) -> None:
        """The `dev_set_promiscuity(master, 1)` form maps to enabled True."""

        content = "vlan1: dev_set_promiscuity(master, 1)"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventKernel.PROMISCUOUS_MODE,
            _KEY.RAW: content,
            _KEY.INTERFACE: "vlan1",
            _KEY.ENABLED: True,
        }

    def test_set_promiscuity_off(self) -> None:
        """The `dev_set_promiscuity(master, 0)` form maps to enabled False."""

        content = "vlan1: dev_set_promiscuity(master, 0)"

        assert _translate(content)[_KEY.ENABLED] is False


class TestStation:
    """Station-related kernel message translation."""

    def test_sbf_init(self) -> None:
        """The client MAC is extracted, opaque fields stay in the raw."""

        content = f"SBF: dhd0: INIT [{_CLIENT}] ID 65535 BFW 65535 THRSH 2048"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventKernel.SBF_INIT,
            _KEY.RAW: classified(content, IDENTIFIER),
            _KEY.CLIENT_MAC: MacAddress.from_value(_CLIENT),
        }

    def test_scb_deauthorize(self) -> None:
        """The parenthesised `error (N)` form is parsed."""

        content = "WLC_SCB_DEAUTHORIZE error (-30)"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventKernel.SCB_DEAUTH_ERROR,
            _KEY.RAW: content,
            _KEY.COMMAND: "WLC_SCB_DEAUTHORIZE",
            _KEY.ERROR: -30,
        }

    def test_scb_deauthenticate(self) -> None:
        """The bare `err N` form is parsed with its command."""

        content = "WLC_SCB_DEAUTHENTICATE_FOR_REASON err -30"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventKernel.SCB_DEAUTH_ERROR,
            _KEY.RAW: content,
            _KEY.COMMAND: "WLC_SCB_DEAUTHENTICATE_FOR_REASON",
            _KEY.ERROR: -30,
        }


class TestTranslateKernel:
    """The per-program dispatcher."""

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "some future kernel message we do not handle yet"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventKernel.UNKNOWN,
            _KEY.RAW: unread(content),
        }
