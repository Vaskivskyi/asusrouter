"""MiniUPnP daemon log event translation for AsusRouter."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.identifiers import IpAddress

if TYPE_CHECKING:
    from collections.abc import Callable


class AREventMiniupnp(FromStrMixin, StrEnum):
    """MiniUPnP daemon event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    CHAIN_NOT_FOUND = "chain_not_found"
    EVENT_NOTIFY_FAILED = "event_notify_failed"
    EVENT_RECV_TIMEOUT = "event_recv_timeout"
    HTTP_LISTENING = "http_listening"
    INTERFACE_IP_FAILED = "interface_ip_failed"
    INTERFACE_NAME_ADVISED = "interface_name_advised"
    NAT_PMP_LISTENING = "nat_pmp_listening"
    PEER_NOT_LAN = "peer_not_lan"
    PUBLIC_ADDRESS_FAILED = "public_address_failed"
    SHUTDOWN = "shutdown"
    SUBSCRIBER_REMOVED = "subscriber_removed"


# Every message naming a peer reads its address the same way
_PEER: dict[AREventKey, Callable[[str], Any]] = {
    AREventKey.CLIENT_IP: IpAddress.from_value_safe,
    AREventKey.PORT: int,
}

PATTERNS = ARLogPatternSet(
    AREventMiniupnp.UNKNOWN,
    (
        # A missing iptables chain
        ARLogPattern(
            AREventMiniupnp.CHAIN_NOT_FOUND,
            r"chain (?P<chain>\S+) not found",
            marker="not found",
        ),
        # The failure reason trails the peer and is left in the raw
        ARLogPattern(
            AREventMiniupnp.EVENT_NOTIFY_FAILED,
            r"upnp_event_process_notify: "
            r"connect\((?P<client_ip>[\d.]+):(?P<port>\d+)\)",
            convert=_PEER,
            marker="upnp_event_process_notify",
        ),
        ARLogPattern(
            AREventMiniupnp.EVENT_RECV_TIMEOUT,
            r"upnp_event_recv: recv\(\): Connection timed out",
            marker="upnp_event_recv",
        ),
        ARLogPattern(
            AREventMiniupnp.HTTP_LISTENING,
            r"HTTP listening on port (?P<port>\d+)",
            convert={AREventKey.PORT: int},
            marker="HTTP listening on port",
        ),
        ARLogPattern(
            AREventMiniupnp.INTERFACE_IP_FAILED,
            r"Failed to get ip address for interface",
            marker="Failed to get ip address",
        ),
        # The daemon was configured with an address where it wants a name
        ARLogPattern(
            AREventMiniupnp.INTERFACE_NAME_ADVISED,
            r"use network interface name instead of "
            r"(?P<local_ip>[\d.]+)/(?P<netmask>[\d.]+)",
            convert={
                AREventKey.LOCAL_IP: IpAddress.from_value_safe,
                AREventKey.NETMASK: IpAddress.from_value_safe,
            },
            marker="use network interface name instead",
        ),
        # Same failure, worded differently on older firmware
        ARLogPattern(
            AREventMiniupnp.INTERFACE_IP_FAILED,
            r"Cannot get IP address for ext interface",
            marker="Cannot get IP address",
        ),
        ARLogPattern(
            AREventMiniupnp.NAT_PMP_LISTENING,
            r"Listening for NAT-PMP/PCP traffic on port (?P<port>\d+)",
            convert={AREventKey.PORT: int},
            marker="NAT-PMP/PCP traffic",
        ),
        ARLogPattern(
            AREventMiniupnp.PEER_NOT_LAN,
            r"HTTP peer (?P<client_ip>[\d.]+):(?P<port>\d+) is not from a LAN",
            convert=_PEER,
            marker="is not from a LAN",
        ),
        ARLogPattern(
            AREventMiniupnp.PUBLIC_ADDRESS_FAILED,
            r"SendNATPMPPublicAddressChangeNotification: "
            r"cannot get public IP address",
            marker="cannot get public IP address",
        ),
        ARLogPattern(
            AREventMiniupnp.SHUTDOWN,
            r"shutting down MiniUPnPd",
            marker="shutting down MiniUPnPd",
        ),
        # The callback carries the LAN client `http://<ip>:<port><path>`
        ARLogPattern(
            AREventMiniupnp.SUBSCRIBER_REMOVED,
            r"remove subscriber uuid:(?P<uuid>[0-9A-Fa-f-]+) "
            r"after an ERROR cb: "
            r"\w+://(?P<client_ip>[\d.]+):(?P<port>\d+)(?P<path>\S+)",
            convert=_PEER,
            marker="remove subscriber",
        ),
    ),
)
