"""Tests for the support wifi module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.wifi import (
    translate_wifi,
    translate_wifi_capabilities,
)
from asusrouter.modules.wifi import (
    ARWiFiCapability,
    ARWiFiGeneration,
    ARWiFiMultiBand,
)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        # No capability at all -> no WiFi
        ({}, False),
        # Explicit opt-out wins
        ({ARSupportValue.WIFI_UNIT_NONE.value: 1}, False),
        (
            {
                ARSupportValue.WIFI_UNIT_NONE.value: 1,
                ARSupportValue.WIFI_UNIT_0.value: 1,
            },
            False,
        ),
        # Any real capability -> has WiFi
        ({ARSupportValue.WIFI_UNIT_0.value: 1}, True),
        ({ARSupportValue.WIFI_6.value: 1}, True),
    ],
)
def test_translate_wifi(data: Any, expected: bool) -> None:
    """Test translate_wifi reports whether the device has WiFi."""

    assert translate_wifi(data) is expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, {}),
        # Generation (highest wins)
        (
            {ARSupportValue.WIFI_7.value: 1, ARSupportValue.WIFI_6.value: 1},
            {ARWiFiCapability.GENERATION: ARWiFiGeneration.WIFI_7},
        ),
        # Multiband (quad wins)
        (
            {
                ARSupportValue.WIFI_BANDS_QUAD.value: 1,
                ARSupportValue.WIFI_BANDS_TRI.value: 1,
            },
            {ARWiFiCapability.MULTIBAND: ARWiFiMultiBand.QUADBAND},
        ),
        # Units, in order
        (
            {
                ARSupportValue.WIFI_UNIT_0.value: 1,
                ARSupportValue.WIFI_UNIT_2.value: 1,
            },
            {ARWiFiCapability.UNITS: [0, 2]},
        ),
        # noWiFi drops the units
        ({ARSupportValue.WIFI_UNIT_NONE.value: 1}, {}),
        # Bool radio capability
        (
            {ARSupportValue.WIFI_OFDMA_DL.value: 1},
            {ARWiFiCapability.OFDMA_DL: True},
        ),
        # Smart Connect present only when supported
        (
            {ARSupportValue.WIFI_SMART_CONNECT_V2.value: 1},
            {ARWiFiCapability.SMART_CONNECT: 2},
        ),
        (
            {ARSupportValue.WIFI_BANDSTEERING.value: 1},
            {ARWiFiCapability.SMART_CONNECT: 1},
        ),
        # A full device
        (
            {
                ARSupportValue.WIFI_7.value: 1,
                ARSupportValue.WIFI_BANDS_TRI.value: 1,
                ARSupportValue.WIFI_UNIT_0.value: 1,
                ARSupportValue.WIFI_UNIT_1.value: 1,
                ARSupportValue.WIFI_UNIT_2.value: 1,
                ARSupportValue.WIFI_MBO.value: 1,
                ARSupportValue.WIFI_MLO.value: 1,
                ARSupportValue.WIFI_POWER_CONTROL.value: 1,
                ARSupportValue.WIFI_SMART_CONNECT_V2.value: 1,
            },
            {
                ARWiFiCapability.MBO: True,
                ARWiFiCapability.MLO: True,
                ARWiFiCapability.POWER_CONTROL: True,
                ARWiFiCapability.GENERATION: ARWiFiGeneration.WIFI_7,
                ARWiFiCapability.MULTIBAND: ARWiFiMultiBand.TRIBAND,
                ARWiFiCapability.SMART_CONNECT: 2,
                ARWiFiCapability.UNITS: [0, 1, 2],
            },
        ),
    ],
)
def test_translate_wifi_capabilities(
    data: Any, expected: dict[ARWiFiCapability, Any]
) -> None:
    """Test translate_wifi_capabilities maps present-when-known caps."""

    assert translate_wifi_capabilities(data) == expected
