"""Tests for the WAN module."""

from __future__ import annotations

from asusrouter.modules.wan import ARDualWanMode


class TestARDualWanMode:
    """Tests for ARDualWanMode."""

    def test_values(self) -> None:
        """Members map to their router codes."""

        assert ARDualWanMode.FAILOVER.value == "fo"
        assert ARDualWanMode.FALLBACK.value == "fb"
        assert ARDualWanMode.LOAD_BALANCE.value == "lb"

    def test_from_value_unknown(self) -> None:
        """Unknown input resolves to UNKNOWN."""

        assert ARDualWanMode.from_value("zz") is ARDualWanMode.UNKNOWN
