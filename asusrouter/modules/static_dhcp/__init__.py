"""Static DHCP module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.static_dhcp.action import (
    ARStaticDHCPAction,
    run_action,
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
    parse_static_dhcp_leases,
)
from asusrouter.modules.static_dhcp.source import (
    STATIC_DHCP_REQUEST,
    ARStaticDHCPSource,
    ARStaticDHCPSourceUniversal,
    fetch_state,
    translate_state,
)

__all__ = [
    "STATIC_DHCP_REQUEST",
    "ARStaticDHCPAction",
    "ARStaticDHCPCommand",
    "ARStaticDHCPField",
    "ARStaticDHCPLayout",
    "ARStaticDHCPSource",
    "ARStaticDHCPSourceUniversal",
    "StaticDHCPLease",
    "compile_static_dhcp_leases",
    "fetch_state",
    "normalize_static_dhcp_lease",
    "normalize_static_dhcp_mac",
    "parse_static_dhcp_leases",
    "run_action",
    "translate_state",
]
