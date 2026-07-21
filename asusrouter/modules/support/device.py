"""Supported device modes."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.common.device import AROperationMode
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.tools.readers import is_true_in_dict


def translate_device_mode(data: dict[str, Any]) -> list[AROperationMode]:
    """List the operation modes the device can switch to."""

    modes: list[AROperationMode] = []

    if not is_true_in_dict(ARSupportValue.MODE_NO_ROUTER.value, data):
        modes.append(AROperationMode.ROUTER)

    if is_true_in_dict(ARSupportValue.MODE_REPEATER.value, data):
        modes.append(AROperationMode.REPEATER)

    if not is_true_in_dict(ARSupportValue.MODE_NO_ACCESS_POINT.value, data):
        modes.append(AROperationMode.ACCESS_POINT)

    if is_true_in_dict(
        ARSupportValue.MODE_MEDIA_BRIDGE.value, data
    ) or is_true_in_dict(
        ARSupportValue.MODE_MEDIA_BRIDGE_PROXYSTA.value, data
    ):
        modes.append(AROperationMode.MEDIA_BRIDGE)

    if is_true_in_dict(ARSupportValue.AIMESH_NODE.value, data):
        modes.append(AROperationMode.AIMESH_NODE)

    return modes
