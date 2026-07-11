"""Hook endpoint module."""

from __future__ import annotations

import logging
from typing import Any

from asusrouter.modules.data import AsusData
from asusrouter.modules.ddns import process_ddns
from asusrouter.modules.led import AsusLED
from asusrouter.modules.parental_control import (
    KEY_PC_BLOCK_ALL,
    KEY_PC_STATE,
    AsusBlockAll,
    AsusParentalControl,
    read_pc_rules,
)
from asusrouter.modules.port_forwarding import (
    KEY_PORT_FORWARDING_LIST,
    KEY_PORT_FORWARDING_STATE,
    AsusPortForwarding,
    PortForwardingRule,
)
from asusrouter.tools.converters_v2.raw import raw_to_int, raw_to_str

_LOGGER = logging.getLogger(__name__)

_VPNC_PART_MIN_FIELDS = 7


def process(data: dict[str, Any]) -> dict[AsusData, Any]:  # noqa: C901, PLR0912
    """Process hook data."""

    # For this endpoint, the received data always depends on the sent request.
    # So, we need to check which data is available and process it accordingly.
    # Otherwise, we can accidentally overwrite the data with empty values.

    state: dict[AsusData, Any] = {}

    # DDNS
    if (
        "ddns_return_code_chk" in data
        or "ddns_server_x" in data
        or "ddns_hostname_x" in data
    ):
        state[AsusData.DDNS] = process_ddns(data)

    # LED
    if "led_val" in data:
        _led = raw_to_int(data.get("led_val"))
        state[AsusData.LED] = {
            "state": AsusLED(_led if _led is not None else -999)
        }

    # Parental control
    if KEY_PC_STATE in data:
        state[AsusData.PARENTAL_CONTROL] = process_parental_control(data)

    # Port forwarding
    if KEY_PORT_FORWARDING_STATE in data:
        state[AsusData.PORT_FORWARDING] = process_port_forwarding(data)

    return state


def process_parental_control(data: dict[str, Any]) -> dict[str, Any]:
    """Process parental control data."""

    parental_control: dict[str, Any] = {}

    # State
    parental_control["state"] = AsusParentalControl(
        _v if (_v := raw_to_int(data.get(KEY_PC_STATE))) is not None else -999
    )

    # Block all
    _block_all = raw_to_int(data.get(KEY_PC_BLOCK_ALL))
    parental_control["block_all"] = AsusBlockAll(
        _block_all if _block_all is not None else -999
    )

    # Rules
    parental_control["rules"] = read_pc_rules(data)

    return parental_control


def process_port_forwarding(data: dict[str, Any]) -> dict[str, Any]:
    """Process port forwarding data."""

    port_forwarding = {}

    # State
    port_forwarding["state"] = AsusPortForwarding(
        _v
        if (_v := raw_to_int(data.get(KEY_PORT_FORWARDING_STATE))) is not None
        else -999
    )

    # Rules
    pf_list = data.get(KEY_PORT_FORWARDING_LIST)
    if pf_list:
        rules = []
        rule_list = pf_list.split("&#60")
        for rule in rule_list:
            if rule == "":
                continue
            part = rule.split("&#62")
            rules.append(
                PortForwardingRule(
                    name=raw_to_str(part[0]),
                    ip_address=part[2],
                    port=raw_to_str(part[3]),
                    protocol=part[4],
                    ip_external=raw_to_str(part[5]),
                    port_external=part[1],
                )
            )
        port_forwarding["rules"] = rules.copy()

    return port_forwarding
