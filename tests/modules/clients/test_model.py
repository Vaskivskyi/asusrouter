"""Tests for the clients model."""

from __future__ import annotations

from asusrouter.modules.clients.model import (
    ARClient,
    ARClientConnection,
    ARClientLink,
)
from asusrouter.modules.common.connection import ARConnectionType
from asusrouter.modules.common.device import ARDeviceType
from asusrouter.modules.common.internet import ARInternetMode
from asusrouter.modules.common.ip import ARIPMethod
from asusrouter.modules.wifi import ARWiFiFrequency
from asusrouter.tools.identifiers import MacAddress

_MAC = MacAddress.from_value("AA:BB:CC:DD:EE:FF")


class TestARClientLink:
    """Tests for ARClientLink."""

    def test_defaults(self) -> None:
        """A bare link is all-unknown / empty."""

        link = ARClientLink()
        assert link.frequency is ARWiFiFrequency.UNKNOWN
        assert link.band is None
        assert link.mac is None
        assert link.rssi is None
        assert link.rx_speed is None
        assert link.tx_speed is None
        assert link.connected_since is None


class TestARClientConnection:
    """Tests for ARClientConnection."""

    def test_defaults(self) -> None:
        """A bare connection carries unknown type and empty links."""

        connection = ARClientConnection()
        assert connection.type is ARConnectionType.UNKNOWN
        assert connection.ip is None
        assert connection.ip_method is ARIPMethod.UNKNOWN
        assert connection.internet_access is None
        assert connection.guest is False
        assert connection.mlo is False
        assert connection.links == []

    def test_links_are_independent(self) -> None:
        """Each connection gets its own links list."""

        first = ARClientConnection()
        second = ARClientConnection()
        first.links.append(ARClientLink())
        assert second.links == []


class TestARClient:
    """Tests for ARClient."""

    def test_requires_mac(self) -> None:
        """The MAC is the only required field."""

        client = ARClient(mac=_MAC)
        assert client.mac == _MAC
        assert client.online is False
        assert client.name is None
        assert client.device_type is ARDeviceType.UNKNOWN
        assert client.internet_mode is ARInternetMode.UNKNOWN
        assert client.connection is None
