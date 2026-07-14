"""Tests for the temperature scaling submodule."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from asusrouter.config import ARConfigKey as ARConfKey
from asusrouter.modules.temperature import scale as scale_mod
from asusrouter.modules.temperature.scale import (
    scale_temperature,
    warn_temperature_scaled,
)


class TestScaleTemperature:
    """Tests for scale_temperature."""

    @pytest.mark.parametrize(
        ("temperature", "expected", "expected_scaled"),
        [
            ({"a": 30.0, "b": 40.0}, {"a": 30.0, "b": 40.0}, False),
            ({"a": 0.03, "b": 0.04}, {"a": 30.0, "b": 40.0}, True),
            ({"a": 30000.0, "b": 40000.0}, {"a": 30.0, "b": 40.0}, True),
            ({"a": None}, {}, False),
            ({"a": 0.00003, "b": 0.00004}, {"a": 3.0, "b": 4.0}, True),
            (
                {"a": 30000000.0, "b": 40000000.0},
                {"a": 300.0, "b": 400.0},
                True,
            ),
        ],
        ids=[
            "in_range",
            "scale_up",
            "scale_down",
            "none_ignored",
            "max_steps_up",
            "max_steps_down",
        ],
    )
    def test_scales_into_range(
        self,
        temperature: dict[str, float | None],
        expected: dict[str, float],
        expected_scaled: bool,
    ) -> None:
        """Values are rescaled into [10, 150] within the step budget."""

        result, scaled = scale_temperature(temperature)
        assert result == expected
        assert scaled is expected_scaled

    @pytest.mark.parametrize(
        "temperature",
        [
            {"a": 30.0, "b": 40.0},
            {"a": 0.03},
            {"a": 0.00003},
        ],
        ids=["in_range", "scale_up", "max_steps"],
    )
    def test_deterministic(self, temperature: dict[str, float | None]) -> None:
        """Repeated calls on the same input produce the same output."""

        first = scale_temperature(temperature)
        second = scale_temperature(temperature)
        assert first == second


class TestWarnTemperatureScaled:
    """Tests for warn_temperature_scaled."""

    @pytest.mark.parametrize(
        ("already_notified", "expect_warn"),
        [(False, True), (True, False)],
        ids=["not_notified_warns", "already_notified_silent"],
    )
    def test_warns_once(
        self, already_notified: bool, expect_warn: bool
    ) -> None:
        """Warns and sets the flag only when not yet notified."""

        config: Any = MagicMock()
        config.get.return_value = already_notified

        with patch.object(scale_mod._LOGGER, "warning") as mock_warn:
            warn_temperature_scaled(config, {"key": "val"})

        config.ensure_notification_flag.assert_called_once_with(
            ARConfKey.NOTIFIED_OPTIMISTIC_TEMPERATURE
        )
        assert mock_warn.called is expect_warn
        assert config.set.called is expect_warn
