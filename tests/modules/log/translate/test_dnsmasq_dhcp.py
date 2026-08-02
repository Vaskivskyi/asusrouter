"""Tests for the DHCP server (dnsmasq-dhcp) event translation."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.dnsmasq_dhcp import (
    PATTERNS,
    AREventDnsmasqDhcp,
)
from asusrouter.tools.identifiers import IpAddress, MacAddress
from tests.modules.log.translate import IDENTIFIER, classified, unread

_KEY = AREventKey
_IP = "192.168.1.11"
_MAC = "aa:bb:cc:00:00:24"


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw DHCP server message."""

    return PATTERNS.translate(content)


class TestTranslateDnsmasqDhcp:
    """The per-program dispatcher."""

    def test_request(self) -> None:
        """A request carries interface, address and client MAC, no hostname."""

        content = f"DHCPREQUEST(br0) {_IP} {_MAC}"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventDnsmasqDhcp.REQUEST,
            _KEY.RAW: classified(content, IDENTIFIER),
            _KEY.INTERFACE: "br0",
            _KEY.CLIENT_IP: IpAddress.from_value(_IP),
            _KEY.CLIENT_MAC: MacAddress.from_value(_MAC),
        }

    def test_ack_with_hostname(self) -> None:
        """An ack additionally carries the client hostname."""

        content = f"DHCPACK(br0) {_IP} {_MAC} my-device"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventDnsmasqDhcp.ACK,
            _KEY.RAW: classified(content, IDENTIFIER),
            _KEY.INTERFACE: "br0",
            _KEY.CLIENT_IP: IpAddress.from_value(_IP),
            _KEY.CLIENT_MAC: MacAddress.from_value(_MAC),
            _KEY.HOSTNAME: "my-device",
        }

    def test_unknown_verb_keeps_data(self) -> None:
        """An unconfirmed verb still yields parsed fields, typed UNKNOWN."""

        event = _translate(f"DHCPRELEASE(br0) {_IP} {_MAC}")

        assert event[_KEY.EVENT_TYPE] is AREventDnsmasqDhcp.UNKNOWN
        assert event[_KEY.CLIENT_IP] == IpAddress.from_value(_IP)
        assert _KEY.HOSTNAME not in event

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "DHCP range 192.168.1.2 -- 192.168.1.254"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventDnsmasqDhcp.UNKNOWN,
            _KEY.RAW: unread(content),
        }
