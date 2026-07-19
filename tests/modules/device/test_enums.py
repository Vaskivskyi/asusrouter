"""Tests for the device enums."""

from __future__ import annotations

import pytest

from asusrouter.const import UNKNOWN_MEMBER
from asusrouter.modules.device.enums import AROperationMode


class TestAROperationMode:
    """Tests for AROperationMode."""

    @pytest.mark.parametrize(
        ("name", "value"),
        [
            ("UNKNOWN", UNKNOWN_MEMBER),
            ("ROUTER", 1),
            ("REPEATER", 2),
            ("ACCESS_POINT", 3),
            ("MEDIA_BRIDGE", 4),
            ("AIMESH_NODE", 5),
        ],
    )
    def test_members_and_values(self, name: str, value: int) -> None:
        """Members exist and carry the expected integer values."""

        member = getattr(AROperationMode, name)
        assert member.name == name
        assert member.value == value

    @pytest.mark.parametrize("member", list(AROperationMode))
    def test_value_round_trip(self, member: AROperationMode) -> None:
        """Every member resolves from its own stored value."""

        assert AROperationMode.from_value(member.value) is member

    def test_unknown_fallback(self) -> None:
        """An unrecognised code falls back to UNKNOWN."""

        assert AROperationMode.from_value(99) is AROperationMode.UNKNOWN
