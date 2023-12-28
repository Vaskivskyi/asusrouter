"""Legacy tools module."""

from __future__ import annotations

from typing import Optional

from asusrouter.modules.port_forwarding import (
    KEY_PORT_FORWARDING_LIST,
    PortForwardingRule,
)


def compile_port_forwarding(data: list[PortForwardingRule]) -> Optional[dict[str, str]]:
    """Compile port forwarding rules"""

    if not isinstance(data, list):
        return None

    result = ""
    for rule in data:
        name = str()
        if rule.name is not None and rule.name != "None":
            name = rule.name
        port_external = str()
        if rule.port_external is not None and rule.port_external != "None":
            port_external = rule.port_external
        ip = str()
        if rule.ip_address is not None and rule.ip_address != "None":
            ip = rule.ip_address
        port = str()
        if rule.port is not None and rule.port != "None":
            port = rule.port
        protocol = str()
        if rule.protocol is not None and rule.protocol != "None":
            protocol = rule.protocol
        ip_external = str()
        if rule.ip_external is not None and rule.ip_external != "None":
            ip_external = rule.ip_external

        result += f"<{name}>{port_external}>{ip}>{port}>{protocol}>{ip_external}>"

    return {
        KEY_PORT_FORWARDING_LIST: result,
    }
