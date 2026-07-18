"""Tests for the NVRAM module."""

from __future__ import annotations

from asusrouter.modules.endpoint.hooks import ARHook
from asusrouter.modules.nvram import ARNvramType


class TestAsHook:
    """Tests for as_hook rendering."""

    def test_type(self) -> None:
        """A flat NVRAM type renders its raw key."""

        assert ARNvramType.MAC.as_hook() == (ARHook.NVRAM_GET, "label_mac")
