"""Tests for asusrouter.modules.common.metrics."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.common.metrics import ARMetricType


class TestARMetricType:
    """Tests for ARMetricType."""

    def test_usage_value(self) -> None:
        """USAGE maps to its string value."""

        assert ARMetricType.USAGE.value == "usage"

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("usage", ARMetricType.USAGE),
            ("other", ARMetricType.UNKNOWN),
            (None, ARMetricType.UNKNOWN),
        ],
    )
    def test_from_value(self, value: Any, expected: ARMetricType) -> None:
        """from_value maps known strings, falls back to UNKNOWN."""

        assert ARMetricType.from_value(value) == expected
