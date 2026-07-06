"""Service module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.service.action import (
    ARServiceAction,
    ARServiceInput,
    ARServiceResult,
    build_service_request,
    read_service_result,
    run_action,
)
from asusrouter.modules.service.legacy import async_call_service

__all__ = [
    "ARServiceAction",
    "ARServiceInput",
    "ARServiceResult",
    "async_call_service",
    "build_service_request",
    "read_service_result",
    "run_action",
]
