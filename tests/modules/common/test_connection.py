"""Tests for the common connection enums."""

from __future__ import annotations

from asusrouter.modules.common.connection import (
    ARConnectionMethod,
    ARConnectionStatus,
    ARConnectionType,
)


def test_values() -> None:
    """Members map to their string values."""

    assert ARConnectionType.WIRED.value == "wired"
    assert ARConnectionType.WIRELESS.value == "wireless"


def test_from_value_unknown() -> None:
    """Unknown input resolves to UNKNOWN."""

    assert ARConnectionType.from_value("nope") is ARConnectionType.UNKNOWN


class TestARConnectionMethod:
    """Tests for ARConnectionMethod."""

    def test_values(self) -> None:
        """Members map to their string values."""

        assert ARConnectionMethod.DHCP.value == "dhcp"
        assert ARConnectionMethod.STATIC.value == "static"
        assert ARConnectionMethod.PPPOE.value == "pppoe"
        assert ARConnectionMethod.PPTP.value == "pptp"
        assert ARConnectionMethod.L2TP.value == "l2tp"

    def test_from_value_unknown(self) -> None:
        """Unknown input resolves to UNKNOWN."""

        assert ARConnectionMethod.from_value("nope") is (
            ARConnectionMethod.UNKNOWN
        )


class TestARConnectionStatus:
    """Tests for ARConnectionStatus."""

    def test_values(self) -> None:
        """Members map to their router codes."""

        assert ARConnectionStatus.ERROR == -1
        assert ARConnectionStatus.DISCONNECTED == 0
        assert ARConnectionStatus.CONNECTING == 1
        assert ARConnectionStatus.CONNECTED == 2

    def test_from_value(self) -> None:
        """Raw int-like values resolve to the matching member."""

        assert ARConnectionStatus.from_value("2") is (
            ARConnectionStatus.CONNECTED
        )
        assert ARConnectionStatus.from_value(0) is (
            ARConnectionStatus.DISCONNECTED
        )

    def test_from_value_unknown(self) -> None:
        """Unmapped codes resolve to UNKNOWN."""

        assert ARConnectionStatus.from_value(99) is ARConnectionStatus.UNKNOWN
        assert ARConnectionStatus.from_value("nope") is (
            ARConnectionStatus.UNKNOWN
        )
