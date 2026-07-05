"""Tests for the network common helpers."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.network.common import (
    bandwidth_limit,
    decode,
    mac_filter_mode,
    read_mac_list,
)
from asusrouter.modules.network.enums import ARNetworkField
from asusrouter.modules.wifi import ARWiFiMacFilterMode
from asusrouter.tools.identifiers import MacAddress

_MAC = "AA:BB:CC:DD:EE:FF"


class TestDecode:
    """Tests for decode."""

    def test_entities(self) -> None:
        """The char entities decode to angle brackets."""

        assert decode("&#60a&#62b") == "<a>b"

    def test_non_string(self) -> None:
        """A non-string decodes to empty."""

        assert decode(None) == ""


class TestReadMacList:
    """Tests for read_mac_list."""

    def test_extracts(self) -> None:
        """MACs are extracted from the encoded list."""

        assert read_mac_list(f"&#60{_MAC}&#62") == [MacAddress(_MAC)]

    def test_empty(self) -> None:
        """A list with no MACs is empty."""

        assert read_mac_list("") == []


class TestMacFilterMode:
    """Tests for mac_filter_mode."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("0", ARWiFiMacFilterMode.DISABLED),
            ("disabled", ARWiFiMacFilterMode.DISABLED),
            ("1", ARWiFiMacFilterMode.ALLOW),
            ("allow", ARWiFiMacFilterMode.ALLOW),
            ("2", ARWiFiMacFilterMode.DENY),
            ("deny", ARWiFiMacFilterMode.DENY),
        ],
    )
    def test_known(self, raw: str, expected: ARWiFiMacFilterMode) -> None:
        """Known values map to the mode."""

        assert mac_filter_mode(raw) is expected

    @pytest.mark.parametrize("raw", ["x", None])
    def test_unknown(self, raw: Any) -> None:
        """Unknown values yield None."""

        assert mac_filter_mode(raw) is None


class TestBandwidthLimit:
    """Tests for bandwidth_limit."""

    def test_enabled(self) -> None:
        """Enabled limiter yields both rates in bits/s (from Kib/s)."""

        assert bandwidth_limit("1", "5120", "2048") == {
            ARNetworkField.BANDWIDTH_LIMIT_DOWNLOAD: 5120 * 1024,
            ARNetworkField.BANDWIDTH_LIMIT_UPLOAD: 2048 * 1024,
        }

    @pytest.mark.parametrize("enabled", ["0", None, ""])
    def test_disabled(self, enabled: Any) -> None:
        """A disabled or missing limiter yields no fields."""

        assert bandwidth_limit(enabled, "5120", "2048") == {}

    def test_missing_rates(self) -> None:
        """Enabled with unparsable rates yields no rate fields."""

        assert bandwidth_limit("1", None, None) == {}
