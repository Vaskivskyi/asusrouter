"""Tests for the MiniUPnP daemon event translation."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.miniupnp import PATTERNS, AREventMiniupnp
from asusrouter.tools.identifiers import IpAddress
from tests.modules.log.translate import IDENTIFIER, classified, unread

_KEY = AREventKey
_PEER = "HTTP peer 10.1.0.2:46167 is not from a LAN, closing the connection"
_SUBSCRIBER = (
    "upnpevents_processfds: 0x210fe8, remove subscriber "
    "uuid:3ddcd1d3-2380-45f5-b069-cc28aaf405c3 after an ERROR cb: "
    "http://192.168.0.2:2869/upnp/eventing/fyumvcmqvt"
)


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw MiniUPnP daemon message."""

    return PATTERNS.translate(content)


class TestTranslateMiniupnp:
    """The per-program dispatcher."""

    def test_chain_not_found(self) -> None:
        """The chain name is extracted."""

        content = "chain VUPNP not found"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventMiniupnp.CHAIN_NOT_FOUND,
            _KEY.RAW: content,
            _KEY.CHAIN: "VUPNP",
        }

    def test_event_recv_timeout(self) -> None:
        """The timeout marker maps to EVENT_RECV_TIMEOUT, no data keys."""

        content = "upnp_event_recv: recv(): Connection timed out"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventMiniupnp.EVENT_RECV_TIMEOUT,
            _KEY.RAW: content,
        }

    def test_interface_ip_failed(self) -> None:
        """The failure marker maps to INTERFACE_IP_FAILED, no data keys."""

        content = "Failed to get ip address for interface"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventMiniupnp.INTERFACE_IP_FAILED,
            _KEY.RAW: content,
        }

    def test_peer_not_lan(self) -> None:
        """The peer address and port are extracted."""

        assert _translate(_PEER) == {
            _KEY.EVENT_TYPE: AREventMiniupnp.PEER_NOT_LAN,
            _KEY.RAW: classified(_PEER, IDENTIFIER),
            _KEY.CLIENT_IP: IpAddress.from_value("10.1.0.2"),
            _KEY.PORT: 46167,
        }

    def test_subscriber_removed(self) -> None:
        """The uuid, callback address, port and path are extracted."""

        assert _translate(_SUBSCRIBER) == {
            _KEY.EVENT_TYPE: AREventMiniupnp.SUBSCRIBER_REMOVED,
            _KEY.RAW: classified(_SUBSCRIBER, IDENTIFIER),
            _KEY.UUID: "3ddcd1d3-2380-45f5-b069-cc28aaf405c3",
            _KEY.CLIENT_IP: IpAddress.from_value("192.168.0.2"),
            _KEY.PORT: 2869,
            _KEY.PATH: "/upnp/eventing/fyumvcmqvt",
        }

    def test_event_notify_failed(self) -> None:
        """The notify callback failure keeps the peer it could not reach."""

        content = (
            "upnp_event_process_notify: connect(192.168.0.2:2869): "
            "Connection timed out"
        )

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventMiniupnp.EVENT_NOTIFY_FAILED,
            _KEY.RAW: classified(content, IDENTIFIER),
            _KEY.CLIENT_IP: IpAddress.from_value("192.168.0.2"),
            _KEY.PORT: 2869,
        }

    def test_http_listening(self) -> None:
        """The HTTP listener reports its port."""

        content = "HTTP listening on port 39733"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventMiniupnp.HTTP_LISTENING,
            _KEY.RAW: content,
            _KEY.PORT: 39733,
        }

    def test_nat_pmp_listening(self) -> None:
        """The NAT-PMP listener reports its port."""

        content = "Listening for NAT-PMP/PCP traffic on port 5351"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventMiniupnp.NAT_PMP_LISTENING,
            _KEY.RAW: content,
            _KEY.PORT: 5351,
        }

    def test_interface_ip_failed_legacy_wording(self) -> None:
        """Older firmware words the same failure differently."""

        content = "Cannot get IP address for ext interface . Network is down"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventMiniupnp.INTERFACE_IP_FAILED,
            _KEY.RAW: content,
        }

    def test_interface_name_advised(self) -> None:
        """The advisory keeps the address it was configured with."""

        content = (
            "it is advised to use network interface name instead of "
            "192.168.1.1/255.255.255.0"
        )

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventMiniupnp.INTERFACE_NAME_ADVISED,
            _KEY.RAW: classified(content, IDENTIFIER),
            _KEY.LOCAL_IP: IpAddress.from_value("192.168.1.1"),
            _KEY.NETMASK: IpAddress.from_value("255.255.255.0"),
        }

    def test_public_address_failed(self) -> None:
        """The NAT-PMP public address failure carries no fields."""

        content = (
            "SendNATPMPPublicAddressChangeNotification: cannot get public "
            "IP address, stopping"
        )

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventMiniupnp.PUBLIC_ADDRESS_FAILED,
            _KEY.RAW: content,
        }

    def test_shutdown(self) -> None:
        """The shutdown marker carries no fields."""

        content = "shutting down MiniUPnPd"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventMiniupnp.SHUTDOWN,
            _KEY.RAW: content,
        }

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "some future miniupnpd message we do not handle yet"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventMiniupnp.UNKNOWN,
            _KEY.RAW: unread(content),
        }
