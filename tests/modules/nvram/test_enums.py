"""Tests for the NVRAM enums."""

from __future__ import annotations

import pytest

from asusrouter.modules.endpoint.hooks import ARHook
from asusrouter.modules.nvram.enums import ARNvramIndexType, ARNvramType


class TestARNvramType:
    """Tests for ARNvramType."""

    @pytest.mark.parametrize("member", list(ARNvramType), ids=lambda m: m.name)
    def test_value_round_trip(self, member: ARNvramType) -> None:
        """Every member resolves from its own raw key."""

        assert ARNvramType.from_value(member.value) is member

    @pytest.mark.parametrize("member", list(ARNvramType), ids=lambda m: m.name)
    def test_as_hook(self, member: ARNvramType) -> None:
        """as_hook renders an nvram_get call for the raw key."""

        assert member.as_hook() == (ARHook.NVRAM_GET, member.value)

    def test_as_hook_example(self) -> None:
        """A known member renders its documented raw key."""

        assert ARNvramType.MAC.as_hook() == (ARHook.NVRAM_GET, "label_mac")

    def test_unknown_fallback(self) -> None:
        """An unrecognised key falls back to UNKNOWN."""

        assert ARNvramType.from_value("no-such-nvram-key") is (
            ARNvramType.UNKNOWN
        )


class TestARNvramIndexType:
    """Tests for ARNvramIndexType."""

    @pytest.mark.parametrize(
        "member", list(ARNvramIndexType), ids=lambda m: m.name
    )
    def test_value_round_trip(self, member: ARNvramIndexType) -> None:
        """Every member resolves from its own template value."""

        assert ARNvramIndexType.from_value(member.value) is member

    @pytest.mark.parametrize(
        "member", list(ARNvramIndexType), ids=lambda m: m.name
    )
    def test_key_resolves_template(self, member: ARNvramIndexType) -> None:
        """key() formats the template with the given index."""

        assert member.key(0) == member.value.format(0)

    def test_key_example(self) -> None:
        """A known template resolves with its index."""

        assert ARNvramIndexType.AP_ENABLE.key("g1") == "apg1_enable"

    def test_unknown_fallback(self) -> None:
        """An unrecognised template falls back to UNKNOWN."""

        assert ARNvramIndexType.from_value("no-such-template") is (
            ARNvramIndexType.UNKNOWN
        )
