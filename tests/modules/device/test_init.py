"""Tests for the device module __init__."""

from __future__ import annotations

import pytest

from asusrouter.const import UNKNOWN_MEMBER
from asusrouter.modules.device import AROperationMode


class TestAROperationMode:
    """Tests for the AROperationMode enum."""

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
    def test_enum_members_and_values(self, name: str, value: int) -> None:
        """Enum members exist and have the expected integer values."""

        member = getattr(AROperationMode, name)
        assert member.name == name
        assert member.value == value
