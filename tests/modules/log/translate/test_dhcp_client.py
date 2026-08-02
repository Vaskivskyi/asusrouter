"""Tests for the DHCP client event translation."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.dhcp_client import (
    PATTERNS,
    AREventDhcpClient,
)
from asusrouter.tools.identifiers import IpAddress
from tests.modules.log.translate import IDENTIFIER, classified, unread

_KEY = AREventKey
_BOUND = "bound 192.168.0.2/255.255.255.0 via 192.168.0.1 for 86400 seconds."


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw DHCP client message."""

    return PATTERNS.translate(content)


class TestTranslateDhcpClient:
    """The per-program dispatcher."""

    def test_bound(self) -> None:
        """Address, netmask, gateway and lease seconds are extracted."""

        assert _translate(_BOUND) == {
            _KEY.EVENT_TYPE: AREventDhcpClient.BOUND,
            _KEY.RAW: classified(_BOUND, IDENTIFIER),
            _KEY.LOCAL_IP: IpAddress.from_value("192.168.0.2"),
            _KEY.NETMASK: IpAddress.from_value("255.255.255.0"),
            _KEY.GATEWAY: IpAddress.from_value("192.168.0.1"),
            _KEY.LEASE_SECONDS: 86400,
        }

    def test_deconfig(self) -> None:
        """The marker maps to DECONFIG, no data keys."""

        assert _translate("deconfig") == {
            _KEY.EVENT_TYPE: AREventDhcpClient.DECONFIG,
            _KEY.RAW: "deconfig",
        }

    def test_lease_fail(self) -> None:
        """The marker maps to LEASE_FAIL, no data keys."""

        assert _translate("leasefail") == {
            _KEY.EVENT_TYPE: AREventDhcpClient.LEASE_FAIL,
            _KEY.RAW: "leasefail",
        }

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        assert _translate("renew") == {
            _KEY.EVENT_TYPE: AREventDhcpClient.UNKNOWN,
            _KEY.RAW: unread("renew"),
        }
