"""Tests for the support module flags."""

from __future__ import annotations

import pytest

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.support.flag import ARSupportType, ARSupportValue


class TestARSupportType:
    """Tests for ARSupportType."""

    def test_unknown_value(self) -> None:
        """UNKNOWN carries the sentinel value."""

        assert ARSupportType.UNKNOWN.value == UNKNOWN_MEMBER_STR

    @pytest.mark.parametrize("member", list(ARSupportType))
    def test_value_round_trip(self, member: ARSupportType) -> None:
        """Every member resolves from its own raw value."""

        assert ARSupportType.from_value(member.value) is member

    def test_unknown_fallback(self) -> None:
        """An unrecognised value falls back to UNKNOWN."""

        assert ARSupportType.from_value("no-such-flag") is (
            ARSupportType.UNKNOWN
        )


class TestARSupportValue:
    """Tests for ARSupportValue."""

    def test_unknown_value(self) -> None:
        """UNKNOWN carries the sentinel value."""

        assert ARSupportValue.UNKNOWN.value == UNKNOWN_MEMBER_STR

    @pytest.mark.parametrize("member", list(ARSupportValue))
    def test_value_round_trip(self, member: ARSupportValue) -> None:
        """Every member resolves from its own raw value."""

        assert ARSupportValue.from_value(member.value) is member

    def test_unknown_fallback(self) -> None:
        """An unrecognised value falls back to UNKNOWN."""

        assert ARSupportValue.from_value("no-such-value") is (
            ARSupportValue.UNKNOWN
        )
