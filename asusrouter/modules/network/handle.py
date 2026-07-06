"""Network profile handle for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass

from asusrouter.modules.network.enums import ARNetworkBackend


@dataclass(frozen=True)
class ARNetworkHandle:
    """Opaque round-trip target for enabling or disabling a network."""

    backend: ARNetworkBackend

    # SDN
    sdn_idx: int | None = None
    ap_prefix: str | None = None
    ap_idx: int | None = None

    # Legacy
    units: tuple[tuple[int, int | None], ...] = ()


__all__ = [
    "ARNetworkHandle",
]
