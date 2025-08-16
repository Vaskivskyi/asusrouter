"""Tests for device module."""

import pytest

from asusrouter.const import UNKNOWN_MEMBER
from asusrouter.modules.device import DeviceOperationMode


class TestDeviceOperationMode:
    """Tests for the DeviceOperationMode enum."""

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

        member = getattr(DeviceOperationMode, name)
        assert member.name == name
        assert member.value == value
