"""AiMesh module for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARAiMeshCapability(FromStrMixin, StrEnum):
    """AiMesh capabilities."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    NEW_ONBOARDING = "new_onboarding"
    NODE = "node"
    ROUTER = "router"


# TODO: Redo this legacy class
@dataclass
class AiMeshDevice:
    """AiMesh device class."""

    # Status
    status: bool = False

    alias: str | None = None
    model: str | None = None
    product_id: str | None = None
    ip: str | None = None

    fw: str | None = None
    fw_new: str | None = None

    mac: str | None = None

    # Access point: ap2g, ap5g, ap5g1, ap6g, apdwb
    ap: dict[str, Any] | None = None
    # Parent AiMesh: pap2g, rssi2g, pap2g_ssid, pap5g, rssi5g, pap5g_ssid,
    #                pap6g, rssi6g, pap6g_ssid
    parent: dict[str, Any] | None = None
    # Node state
    type: str | None = None
    level: int | None = None
    config: dict[str, Any] | None = None
