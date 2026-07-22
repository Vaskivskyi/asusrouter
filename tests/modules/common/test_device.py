"""Tests for the common device enums."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.const import UNKNOWN_MEMBER
from asusrouter.modules.common.device import ARDeviceType, AROperationMode


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (5, ARDeviceType.IP_CAM),
        ("9", ARDeviceType.ANDROID_PHONE),
        (137, ARDeviceType.UNKNOWN),
        (None, ARDeviceType.UNKNOWN),
        ("nope", ARDeviceType.UNKNOWN),
    ],
    ids=["int", "str", "special", "none", "bad"],
)
def test_from_value(value: Any, expected: ARDeviceType) -> None:
    """Known codes resolve; unknown / special codes fall back."""

    assert ARDeviceType.from_value(value) is expected


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
