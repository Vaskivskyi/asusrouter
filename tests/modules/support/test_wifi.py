"""Tests for the support wifi module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.wifi import (
    translate_wifi_generation,
    translate_wifi_multiband,
    translate_wifi_units,
)
from asusrouter.modules.wifi import ARWiFiGeneration, ARWiFiMultiBand


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, ARWiFiGeneration.UNKNOWN),
        ({ARSupportValue.WIFI_7.value: 1}, ARWiFiGeneration.WIFI_7),
        ({ARSupportValue.WIFI_6.value: 1}, ARWiFiGeneration.WIFI_6),
        ({ARSupportValue.WIFI_5.value: 1}, ARWiFiGeneration.WIFI_5),
        # Multiple true, should return the highest (first in table)
        (
            {ARSupportValue.WIFI_7.value: 1, ARSupportValue.WIFI_6.value: 1},
            ARWiFiGeneration.WIFI_7,
        ),
        (
            {ARSupportValue.WIFI_6.value: 1, ARSupportValue.WIFI_5.value: 1},
            ARWiFiGeneration.WIFI_6,
        ),
        (
            {
                ARSupportValue.WIFI_7.value: 0,
                ARSupportValue.WIFI_6.value: 0,
                ARSupportValue.WIFI_5.value: 0,
            },
            ARWiFiGeneration.UNKNOWN,
        ),
        (
            {ARSupportValue.WIFI_7.value: "enabled"},
            ARWiFiGeneration.WIFI_7,
        ),
        ({ARSupportValue.WIFI_6.value: "on"}, ARWiFiGeneration.WIFI_6),
        ({ARSupportValue.WIFI_5.value: "1"}, ARWiFiGeneration.WIFI_5),
        # Not a dict
        ("not_a_dict", ARWiFiGeneration.UNKNOWN),
    ],
)
def test_translate_wifi_generation(
    data: dict[str, Any], expected: ARWiFiGeneration
) -> None:
    """Test translate_wifi_generation returns correct generation type."""

    result = translate_wifi_generation(data)
    assert result == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, ARWiFiMultiBand.UNKNOWN),
        (
            {ARSupportValue.WIFI_BANDS_QUAD.value: 1},
            ARWiFiMultiBand.QUADBAND,
        ),
        (
            {ARSupportValue.WIFI_BANDS_TRI.value: 1},
            ARWiFiMultiBand.TRIBAND,
        ),
        (
            {ARSupportValue.WIFI_BANDS_DUAL.value: 1},
            ARWiFiMultiBand.DUALBAND,
        ),
        # Multiple true, should return the highest (quad > tri > dual)
        (
            {
                ARSupportValue.WIFI_BANDS_QUAD.value: 1,
                ARSupportValue.WIFI_BANDS_TRI.value: 1,
            },
            ARWiFiMultiBand.QUADBAND,
        ),
        (
            {
                ARSupportValue.WIFI_BANDS_TRI.value: 1,
                ARSupportValue.WIFI_BANDS_DUAL.value: 1,
            },
            ARWiFiMultiBand.TRIBAND,
        ),
        (
            {
                ARSupportValue.WIFI_BANDS_QUAD.value: 0,
                ARSupportValue.WIFI_BANDS_TRI.value: 0,
                ARSupportValue.WIFI_BANDS_DUAL.value: 0,
            },
            ARWiFiMultiBand.UNKNOWN,
        ),
        (
            {ARSupportValue.WIFI_BANDS_QUAD.value: "enabled"},
            ARWiFiMultiBand.QUADBAND,
        ),
        (
            {ARSupportValue.WIFI_BANDS_TRI.value: "on"},
            ARWiFiMultiBand.TRIBAND,
        ),
        (
            {ARSupportValue.WIFI_BANDS_DUAL.value: "1"},
            ARWiFiMultiBand.DUALBAND,
        ),
        # Not a dict
        ("not_a_dict", ARWiFiMultiBand.UNKNOWN),
    ],
)
def test_translate_wifi_multiband(
    data: dict[str, Any], expected: ARWiFiMultiBand
) -> None:
    """Test translate_wifi_multiband returns correct multiband type."""

    result = translate_wifi_multiband(data)
    assert result == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, []),
        ({ARSupportValue.WIFI_UNIT_NONE.value: 1}, []),
        ({ARSupportValue.WIFI_UNIT_0.value: 1}, [0]),
        ({ARSupportValue.WIFI_UNIT_1.value: 1}, [1]),
        ({ARSupportValue.WIFI_UNIT_2.value: 1}, [2]),
        (
            {
                ARSupportValue.WIFI_UNIT_0.value: 1,
                ARSupportValue.WIFI_UNIT_1.value: 1,
            },
            [0, 1],
        ),
        (
            {
                ARSupportValue.WIFI_UNIT_0.value: 1,
                ARSupportValue.WIFI_UNIT_2.value: 1,
            },
            [0, 2],
        ),
        (
            {
                ARSupportValue.WIFI_UNIT_1.value: 1,
                ARSupportValue.WIFI_UNIT_2.value: 1,
            },
            [1, 2],
        ),
        (
            {
                ARSupportValue.WIFI_UNIT_0.value: 1,
                ARSupportValue.WIFI_UNIT_1.value: 1,
                ARSupportValue.WIFI_UNIT_2.value: 1,
            },
            [0, 1, 2],
        ),
        (
            {
                ARSupportValue.WIFI_UNIT_0.value: 0,
                ARSupportValue.WIFI_UNIT_1.value: 0,
                ARSupportValue.WIFI_UNIT_2.value: 0,
            },
            [],
        ),
        ({ARSupportValue.WIFI_UNIT_0.value: "enabled"}, [0]),
        ({ARSupportValue.WIFI_UNIT_1.value: "on"}, [1]),
        ({ARSupportValue.WIFI_UNIT_2.value: "1"}, [2]),
        # Not a dict
        ("not_a_dict", []),
    ],
)
def test_translate_wifi_units(
    data: dict[str, Any], expected: list[int]
) -> None:
    """Test translate_wifi_units returns correct unit indices."""

    result = translate_wifi_units(data)
    assert result == expected
