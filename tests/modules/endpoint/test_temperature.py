"""Tests for the Temperature endpoint module."""

from typing import Any
from unittest.mock import call, patch

from asusrouter.config import ARConfig, ARConfigKey
from asusrouter.modules.data import AsusData
from asusrouter.modules.endpoint import temperature as temp_mod
from asusrouter.modules.endpoint.temperature import _scale_temperature, process
from asusrouter.modules.wlan import Wlan
import pytest


@pytest.fixture(autouse=True)
def reset_config() -> None:
    """Reset the configuration before each test."""

    ARConfig.set(ARConfigKey.OPTIMISTIC_TEMPERATURE, False)


@pytest.mark.parametrize(
    ("mock_vars", "expected", "optimistic", "scaled"),
    [
        # Normal values, no scaling
        (
            {
                "curr_coreTmp_2_raw": "42",
                "curr_coreTmp_5_raw": "43",
                "curr_coreTmp_52_raw": "44",
                "curr_coreTmp_cpu": "45",
            },
            {
                Wlan.FREQ_2G: 42.0,
                Wlan.FREQ_5G: 43.0,
                Wlan.FREQ_5G2: 44.0,
                "cpu": 45.0,
            },
            False,
            False,
        ),
        # Values need scaling
        (
            {
                "curr_coreTmp_0_raw": "0.04",
                "curr_coreTmp_1_raw": "0.05",
                "curr_coreTmp_2_raw": "0.06",
                "curr_coreTmp_3_raw": "0.07",
                "curr_coreTmp_cpu": "0.08",
            },
            {
                Wlan.FREQ_2G: 40.0,
                Wlan.FREQ_5G: 50.0,
                Wlan.FREQ_5G2: 60.0,
                Wlan.FREQ_6G: 70.0,
                "cpu": 80.0,
            },
            True,
            True,
        ),
        # Disabled value
        (
            {
                "curr_coreTmp_wl0_raw": "disabled",
                "curr_coreTmp_wl1_raw": "43",
                "curr_coreTmp_wl2_raw": "44",
                "curr_coreTmp_wl3_raw": "45",
                "curr_coreTmp_cpu": "46",
            },
            {
                Wlan.FREQ_5G: 43.0,
                Wlan.FREQ_5G2: 44.0,
                Wlan.FREQ_6G: 45.0,
                "cpu": 46.0,
            },
            False,
            False,
        ),
        # CPU temp only
        (
            {"curr_cpuTemp": "55"},
            {"cpu": 55.0},
            False,
            False,
        ),
    ],
)
def test_read_mocked(
    mock_vars: dict[str, str | None],
    expected: dict[str, float],
    optimistic: bool,
    scaled: bool,
) -> None:
    """Test the read function."""

    ARConfig.set(ARConfigKey.OPTIMISTIC_TEMPERATURE, optimistic)
    temp_mod._temperature_warned = False

    with (
        patch.object(
            temp_mod, "clean_content", side_effect=lambda x: x
        ) as mock_clean,
        patch.object(
            temp_mod, "read_js_variables", side_effect=lambda x: mock_vars
        ) as mock_js,
        patch.object(
            temp_mod,
            "safe_float",
            side_effect=lambda x: float(x) if x != "disabled" else None,
        ) as mock_float,
        patch.object(
            temp_mod,
            "_scale_temperature",
            side_effect=lambda temp: (expected, scaled),
        ) as mock_scale,
    ):
        result = temp_mod.read("dummy_content")
        assert result == expected

        # Check that clean_content and read_js_variables are called once
        mock_clean.assert_called_once_with("dummy_content")
        mock_js.assert_called_once_with("dummy_content")

        # safe_float should be called for each value except "disabled"
        float_calls = [
            call(v)
            for v in mock_vars.values()
            if v is not None and v != "disabled"
        ]
        mock_float.assert_has_calls(float_calls, any_order=True)

        # _scale_temperature should be called only if optimistic is True
        if optimistic:
            mock_scale.assert_called_once()
        else:
            mock_scale.assert_not_called()


@pytest.mark.parametrize(
    "input",
    [
        {"val1": 30.0},
        {"val1": 30.0, "val2": 40.0},
        {"val1": "anything", "val2": None},
    ],
)
def test_process(input: dict[str, Any]) -> None:
    """Test the process function."""

    result = process(input)
    assert result.get(AsusData.TEMPERATURE) == input


@pytest.mark.parametrize(
    ("temperature", "result_temperature", "result_scaled"),
    [
        # No scaling needed
        ({"val1": 30.0, "val2": 40.0}, {"val1": 30.0, "val2": 40.0}, False),
        # Scaling up needed (3 orders of magnitude off down)
        ({"val1": 0.03, "val2": 0.04}, {"val1": 30.0, "val2": 40.0}, True),
        # Scaling down needed (3 orders of magnitude off up)
        (
            {"val1": 30000.0, "val2": 40000.0},
            {"val1": 30.0, "val2": 40.0},
            True,
        ),
        # None in the input should be ignored
        ({"val1": None}, {}, False),
        # Scaling needed for 6 orders of magnitude -> this should not happen
        # fully - we allow only 5 steps of scaling
        ({"val1": 0.00003, "val2": 0.00004}, {"val1": 3.0, "val2": 4.0}, True),
        (
            {"val1": 30000000.0, "val2": 40000000.0},
            {"val1": 300.0, "val2": 400.0},
            True,
        ),
    ],
)
def test_scale_temperature(
    temperature: dict[str, float | None],
    result_temperature: dict[str, float],
    result_scaled: bool,
) -> None:
    """Test the _scale_temperature function."""

    scaled_temperature, scaled = _scale_temperature(temperature)
    assert scaled_temperature == result_temperature
    assert scaled == result_scaled
    scaled_temperature, scaled = _scale_temperature(temperature)
    assert scaled_temperature == result_temperature
    assert scaled == result_scaled
