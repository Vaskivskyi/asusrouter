"""Tests for asusrouter.modules.ports.speed."""

from __future__ import annotations

import pytest

from asusrouter.modules.ports.enums import ARPortSpeed


class TestARPortSpeed:
    """Tests for ARPortSpeed."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0, ARPortSpeed.DOWN),
            (10, ARPortSpeed.MBPS_10),
            (100, ARPortSpeed.MBPS_100),
            (1000, ARPortSpeed.MBPS_1000),
            (2500, ARPortSpeed.MBPS_2500),
            (5000, ARPortSpeed.MBPS_5000),
            (10000, ARPortSpeed.MBPS_10000),
            (999, ARPortSpeed.UNKNOWN),
            (-1, ARPortSpeed.UNKNOWN),
        ],
    )
    def test_from_value(self, value: int, expected: ARPortSpeed) -> None:
        """ARPortSpeed.from_value maps Mbps to the speed grade."""

        assert ARPortSpeed.from_value(value) == expected
