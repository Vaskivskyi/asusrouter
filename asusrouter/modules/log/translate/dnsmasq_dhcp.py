"""DHCP server (dnsmasq-dhcp) log event translation for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.common import MAC_PATTERN
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.identifiers import Hostname, IpAddress, MacAddress


class AREventDnsmasqDhcp(FromStrMixin, StrEnum):
    """DHCP server event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    ACK = "ack"
    REQUEST = "request"


PATTERNS = ARLogPatternSet(
    AREventDnsmasqDhcp.UNKNOWN,
    (
        # `DHCP<VERB>(<iface>) <ip> <mac> [hostname]`; only ACK is named
        ARLogPattern(
            {
                "DHCPACK": AREventDnsmasqDhcp.ACK,
                "DHCPREQUEST": AREventDnsmasqDhcp.REQUEST,
            },
            r"(?P<event_type>DHCP[A-Z]+)\((?P<interface>[^)]+)\)\s+"
            r"(?P<client_ip>[\d.]+)\s+"
            rf"(?P<client_mac>{MAC_PATTERN})(?:\s+(?P<hostname>\S+))?",
            convert={
                AREventKey.CLIENT_IP: IpAddress.from_value_safe,
                AREventKey.CLIENT_MAC: MacAddress.from_value_safe,
                # The name the client asked for - a plain str here would
                # leave it out of the raw message's classification
                AREventKey.HOSTNAME: Hostname.from_value_safe,
            },
            marker="DHCP",
        ),
    ),
)
