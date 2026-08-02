"""Kernel log event translation for AsusRouter."""

from __future__ import annotations

from enum import StrEnum
from functools import partial

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.common import MAC_PATTERN
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.identifiers import MacAddress


class AREventKernel(FromStrMixin, StrEnum):
    """Kernel event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    BRIDGE_PORT_STATE = "bridge_port_state"
    BRIDGE_TOPOLOGY_CHANGE = "bridge_topology_change"
    ETHERNET_LINK_DOWN = "ethernet_link_down"
    ETHERNET_LINK_UP = "ethernet_link_up"
    KLOGD_START = "klogd_start"
    PHY_CAL_INIT = "phy_cal_init"
    PROMISCUOUS_MODE = "promiscuous_mode"
    SBF_INIT = "sbf_init"
    SCB_DEAUTH_ERROR = "scb_deauth_error"
    TASKLET_KILL_ATTEMPT = "tasklet_kill_attempt"
    WIRELESS_CONTROLLER = "wireless_controller"
    WL_MODULE_INIT = "wl_module_init"


# Common ethernet switch-port prefix shared by the link up/down messages
_ETH_PORT = (
    r"(?P<interface>eth\d+)\s+\(Int switch port:\s*(?P<switch_port>\d+)\)\s+"
    r"\(Logical Port:\s*(?P<logical_port>\d+)\)\s+"
    r"\(phyId:\s*(?P<phy_id>[0-9A-Fa-f]+)\)"
)
_ETH_PORT_FIELDS = {
    AREventKey.LOGICAL_PORT: int,
    AREventKey.SWITCH_PORT: int,
}


def _entered(value: str) -> bool:
    """Whether the interface entered rather than left the mode."""

    return value == "entered"


def _on(value: str) -> bool:
    """Whether the driver reports the feature as on."""

    return value == "On"


def _one(value: str) -> bool:
    """Whether the driver flag is set."""

    return value == "1"


PATTERNS = ARLogPatternSet(
    AREventKernel.UNKNOWN,
    (
        ARLogPattern(
            AREventKernel.BRIDGE_PORT_STATE,
            r"(?P<bridge>br\d+): port (?P<port>\d+)"
            r"\((?P<interface>[a-z0-9.]+)\) entering (?P<state>\w+) state",
            convert={AREventKey.PORT: int},
            marker="entering",
        ),
        ARLogPattern(
            AREventKernel.BRIDGE_TOPOLOGY_CHANGE,
            r"(?P<bridge>br\d+): topology change detected",
            marker="topology change detected",
        ),
        ARLogPattern(
            AREventKernel.ETHERNET_LINK_DOWN,
            rf"{_ETH_PORT}\s+Link (?:DOWN|Down)",
            convert=_ETH_PORT_FIELDS,
            marker="Link",
        ),
        ARLogPattern(
            AREventKernel.ETHERNET_LINK_UP,
            rf"{_ETH_PORT}\s+Link (?:UP|Up) at (?P<speed>\d+) mbps "
            r"(?P<duplex>\w+) duplex(?:\s+AN:\s*(?P<autoneg>\w+))?",
            convert={
                **_ETH_PORT_FIELDS,
                AREventKey.AUTONEG: _on,
                AREventKey.SPEED: int,
            },
            marker="Link",
        ),
        ARLogPattern(
            AREventKernel.KLOGD_START,
            r"klogd started: BusyBox v(?P<version>[\d.]+)",
            marker="klogd started",
        ),
        ARLogPattern(
            AREventKernel.PHY_CAL_INIT,
            r"wlc_phy_cal_init_acphy: NOT Implemented",
            marker="wlc_phy_cal_init_acphy",
        ),
        ARLogPattern(
            AREventKernel.PROMISCUOUS_MODE,
            r"device (?P<interface>[a-z0-9.]+) "
            r"(?P<enabled>entered|left) promiscuous mode",
            convert={AREventKey.ENABLED: _entered},
            marker="promiscuous mode",
        ),
        # SBF unknown; only the client MAC is interpreted
        ARLogPattern(
            AREventKernel.SBF_INIT,
            rf"SBF:\s*\w+:\s*INIT\s*\[(?P<client_mac>{MAC_PATTERN})\]",
            convert={AREventKey.CLIENT_MAC: MacAddress.from_value_safe},
            marker="SBF:",
        ),
        # Both driver ioctls fail with -30 (BCME_NOTFOUND) once the
        # station is gone
        ARLogPattern(
            AREventKernel.SCB_DEAUTH_ERROR,
            r"(?P<command>WLC_SCB_[A-Z_]+)\s+"
            r"(?:error\s*\(|err\s+)(?P<error>-?\d+)\)?",
            convert={AREventKey.ERROR: int},
            marker="WLC_SCB_",
        ),
        # `<iface>: dev_set_promiscuity(master, 1)` on the bridge
        ARLogPattern(
            AREventKernel.PROMISCUOUS_MODE,
            r"(?P<interface>[a-z0-9.]+): "
            r"dev_set_promiscuity\(master, (?P<enabled>[01])\)",
            convert={AREventKey.ENABLED: _one},
            marker="dev_set_promiscuity",
        ),
        ARLogPattern(
            AREventKernel.TASKLET_KILL_ATTEMPT,
            r"Attempt to kill tasklet from interrupt",
            marker="Attempt to kill tasklet",
        ),
        ARLogPattern(
            AREventKernel.WIRELESS_CONTROLLER,
            r"(?P<interface>eth\d+): Broadcom (?P<chip>BCM\d+) "
            r"802\.11 Wireless Controller (?P<version>[\d.]+) "
            r"\(r(?P<revision>\d+)\)",
            convert={AREventKey.REVISION: int},
            marker="Wireless Controller",
        ),
        ARLogPattern(
            AREventKernel.WL_MODULE_INIT,
            r"wl_module_init: (?P<parameter>\w+) set to "
            r"(?P<value>0x[0-9A-Fa-f]+)",
            convert={AREventKey.VALUE: partial(int, base=16)},
            marker="wl_module_init:",
        ),
    ),
)
