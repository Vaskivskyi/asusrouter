"""Tests for the common device-type enum."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.common.device import ARDeviceType


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (5, ARDeviceType.IP_CAM),
        ("9", ARDeviceType.ANDROID_PHONE),
        (137, ARDeviceType.UNKNOWN),
        (None, ARDeviceType.UNKNOWN),
        ("nope", ARDeviceType.UNKNOWN),
    ],
    ids=["int", "str", "special", "none", "bad"],
)
def test_from_value(value: Any, expected: ARDeviceType) -> None:
    """Known codes resolve; unknown / special codes fall back."""

    assert ARDeviceType.from_value(value) is expected
