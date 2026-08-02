"""Tests for the support device module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.common.device import AROperationMode
from asusrouter.modules.support.device import translate_device_mode
from asusrouter.modules.support.flag import ARSupportValue


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        # Empty: router and access point are available by default
        ({}, [AROperationMode.ROUTER, AROperationMode.ACCESS_POINT]),
        # Negative flags remove the defaults
        (
            {
                ARSupportValue.MODE_NO_ROUTER.value: 1,
                ARSupportValue.MODE_NO_ACCESS_POINT.value: 1,
            },
            [],
        ),
        (
            {ARSupportValue.MODE_REPEATER.value: 1},
            [
                AROperationMode.ROUTER,
                AROperationMode.REPEATER,
                AROperationMode.ACCESS_POINT,
            ],
        ),
        # Media bridge from either token, deduped
        (
            {
                ARSupportValue.MODE_NO_ROUTER.value: 1,
                ARSupportValue.MODE_NO_ACCESS_POINT.value: 1,
                ARSupportValue.MODE_MEDIA_BRIDGE.value: 1,
                ARSupportValue.MODE_MEDIA_BRIDGE_PROXYSTA.value: 1,
            },
            [AROperationMode.MEDIA_BRIDGE],
        ),
        # AiMesh node from the shared amasNode flag
        (
            {
                ARSupportValue.MODE_NO_ROUTER.value: 1,
                ARSupportValue.MODE_NO_ACCESS_POINT.value: 1,
                ARSupportValue.AIMESH_NODE.value: 1,
            },
            [AROperationMode.AIMESH_NODE],
        ),
        # All five, ordered by mode value
        (
            {
                ARSupportValue.MODE_REPEATER.value: 1,
                ARSupportValue.MODE_MEDIA_BRIDGE.value: 1,
                ARSupportValue.AIMESH_NODE.value: 1,
            },
            [
                AROperationMode.ROUTER,
                AROperationMode.REPEATER,
                AROperationMode.ACCESS_POINT,
                AROperationMode.MEDIA_BRIDGE,
                AROperationMode.AIMESH_NODE,
            ],
        ),
    ],
)
def test_translate_device_mode(
    data: Any, expected: list[AROperationMode]
) -> None:
    """Test translate_device_mode lists supported operation modes."""

    assert translate_device_mode(data) == expected
