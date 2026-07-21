"""Tests for the support wifi module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.wifi import (
    translate_wifi_capabilities,
    translate_wifi_generation,
    translate_wifi_multiband,
    translate_wifi_units,
)
from asusrouter.modules.wifi import (
    ARWiFiCapability,
    ARWiFiGeneration,
    ARWiFiMultiBand,
)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.WIFI_7.value: 1}, ARWiFiGeneration.WIFI_7),
        ({ARSupportValue.WIFI_6.value: 1}, ARWiFiGeneration.WIFI_6),
        ({ARSupportValue.WIFI_5.value: 1}, ARWiFiGeneration.WIFI_5),
        # Highest wins
        (
            {ARSupportValue.WIFI_7.value: 1, ARSupportValue.WIFI_6.value: 1},
            ARWiFiGeneration.WIFI_7,
        ),
        ({}, ARWiFiGeneration.UNKNOWN),
    ],
)
def test_translate_wifi_generation(
    data: dict[str, Any], expected: ARWiFiGeneration
) -> None:
    """Test translate_wifi_generation returns correct generation type."""

    assert translate_wifi_generation(data) == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.WIFI_BANDS_QUAD.value: 1}, ARWiFiMultiBand.QUADBAND),
        ({ARSupportValue.WIFI_BANDS_TRI.value: 1}, ARWiFiMultiBand.TRIBAND),
        ({ARSupportValue.WIFI_BANDS_DUAL.value: 1}, ARWiFiMultiBand.DUALBAND),
        # Quad wins over tri
        (
            {
                ARSupportValue.WIFI_BANDS_QUAD.value: 1,
                ARSupportValue.WIFI_BANDS_TRI.value: 1,
            },
            ARWiFiMultiBand.QUADBAND,
        ),
        ({}, ARWiFiMultiBand.UNKNOWN),
    ],
)
def test_translate_wifi_multiband(
    data: dict[str, Any], expected: ARWiFiMultiBand
) -> None:
    """Test translate_wifi_multiband returns correct multiband type."""

    assert translate_wifi_multiband(data) == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        # SMART_CONNECT is always present; nothing else here
        ({}, {ARWiFiCapability.SMART_CONNECT: 0}),
        (
            {ARSupportValue.WIFI_OFDMA.value: 1},
            {ARWiFiCapability.OFDMA: True, ARWiFiCapability.SMART_CONNECT: 0},
        ),
        # DL-only OFDMA is its own bool capability
        (
            {ARSupportValue.WIFI_OFDMA_DL.value: 1},
            {
                ARWiFiCapability.OFDMA_DL: True,
                ARWiFiCapability.SMART_CONNECT: 0,
            },
        ),
        # Smart Connect v2
        (
            {ARSupportValue.WIFI_SMART_CONNECT_V2.value: 1},
            {ARWiFiCapability.SMART_CONNECT: 2},
        ),
        # Smart Connect v1 from either flag
        (
            {ARSupportValue.WIFI_SMART_CONNECT.value: 1},
            {ARWiFiCapability.SMART_CONNECT: 1},
        ),
        (
            {ARSupportValue.WIFI_BANDSTEERING.value: 1},
            {ARWiFiCapability.SMART_CONNECT: 1},
        ),
        # v2 wins over v1 flags
        (
            {
                ARSupportValue.WIFI_SMART_CONNECT_V2.value: 1,
                ARSupportValue.WIFI_SMART_CONNECT.value: 1,
            },
            {ARWiFiCapability.SMART_CONNECT: 2},
        ),
        (
            {
                ARSupportValue.WIFI_MBO.value: 1,
                ARSupportValue.WIFI_MLO.value: 1,
                ARSupportValue.WIFI_MUMIMO.value: 1,
                ARSupportValue.WIFI_OFDMA.value: 1,
                ARSupportValue.WIFI_OFDMA_DL.value: 1,
                ARSupportValue.WIFI_POWER_CONTROL.value: 1,
                ARSupportValue.WIFI_SMART_CONNECT_V2.value: 1,
            },
            {
                ARWiFiCapability.MBO: True,
                ARWiFiCapability.MLO: True,
                ARWiFiCapability.MUMIMO: True,
                ARWiFiCapability.OFDMA: True,
                ARWiFiCapability.OFDMA_DL: True,
                ARWiFiCapability.POWER_CONTROL: True,
                ARWiFiCapability.SMART_CONNECT: 2,
            },
        ),
    ],
)
def test_translate_wifi_capabilities(
    data: dict[str, Any], expected: dict[ARWiFiCapability, bool | int]
) -> None:
    """Test translate_wifi_capabilities maps caps and Smart Connect level."""

    assert translate_wifi_capabilities(data) == expected


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
