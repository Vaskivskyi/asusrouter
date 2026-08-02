"""DHCP client (udhcpc) log event translation for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.identifiers import IpAddress


class AREventDhcpClient(FromStrMixin, StrEnum):
    """DHCP client event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    BOUND = "bound"
    DECONFIG = "deconfig"
    LEASE_FAIL = "lease_fail"


PATTERNS = ARLogPatternSet(
    AREventDhcpClient.UNKNOWN,
    (
        ARLogPattern(
            AREventDhcpClient.BOUND,
            r"bound (?P<local_ip>[\d.]+)/(?P<netmask>[\d.]+) "
            r"via (?P<gateway>[\d.]+) for (?P<lease_seconds>\d+) seconds",
            convert={
                AREventKey.GATEWAY: IpAddress.from_value_safe,
                AREventKey.LEASE_SECONDS: int,
                AREventKey.LOCAL_IP: IpAddress.from_value_safe,
                AREventKey.NETMASK: IpAddress.from_value_safe,
            },
            marker="bound ",
        ),
        # The interface address was cleared
        ARLogPattern(
            AREventDhcpClient.DECONFIG, r"^deconfig$", marker="deconfig"
        ),
        ARLogPattern(
            AREventDhcpClient.LEASE_FAIL, r"^leasefail$", marker="leasefail"
        ),
    ),
)
