"""Tests for the network common helpers."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.network.common import (
    decode,
    mac_filter_mode,
    read_mac_list,
)
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
