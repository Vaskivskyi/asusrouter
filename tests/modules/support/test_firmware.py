"""Tests for the support firmware module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.firmware import ARFirmwareCapability
from asusrouter.modules.support.firmware import (
    translate_firmware,
    translate_firmware_capabilities,
)
from asusrouter.modules.support.flag import ARSupportValue


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        # Manual upload is available by default
        ({}, True),
        ({ARSupportValue.FIRMWARE_LIVE_UPDATE.value: 1}, True),
        # Opting out of manual upload with no other capability -> none
        ({ARSupportValue.FIRMWARE_NO_MANUAL.value: 1}, False),
    ],
)
def test_translate_firmware(data: Any, expected: bool) -> None:
    """Test translate_firmware reports any firmware capability."""

    assert translate_firmware(data) is expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        # Manual upload present by default
        ({}, {ARFirmwareCapability.MANUAL_UPLOAD: True}),
        # noFwManual removes it
        ({ARSupportValue.FIRMWARE_NO_MANUAL.value: 1}, {}),
        # Live update, plus the default manual upload
        (
            {ARSupportValue.FIRMWARE_LIVE_UPDATE.value: 2},
            {
                ARFirmwareCapability.LIVE_UPDATE: True,
                ARFirmwareCapability.MANUAL_UPLOAD: True,
            },
        ),
        # noupdate disables live update but not manual upload
        (
            {
                ARSupportValue.FIRMWARE_LIVE_UPDATE.value: 1,
                ARSupportValue.FIRMWARE_NO_UPDATE.value: 1,
            },
            {ARFirmwareCapability.MANUAL_UPLOAD: True},
        ),
        # Auto upgrade, beta and revert
        (
            {
                ARSupportValue.FIRMWARE_AUTO_UPGRADE.value: 1,
                ARSupportValue.FIRMWARE_BETA.value: 1,
                ARSupportValue.FIRMWARE_REVERT.value: 1,
                ARSupportValue.FIRMWARE_NO_MANUAL.value: 1,
            },
            {
                ARFirmwareCapability.AUTO_UPGRADE: True,
                ARFirmwareCapability.BETA: True,
                ARFirmwareCapability.REVERT: True,
            },
        ),
    ],
)
def test_translate_firmware_capabilities(
    data: Any, expected: dict[ARFirmwareCapability, bool]
) -> None:
    """Test translate_firmware_capabilities maps firmware capabilities."""

    assert translate_firmware_capabilities(data) == expected
