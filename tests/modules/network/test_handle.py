"""Tests for the network profile handle."""

from __future__ import annotations

import dataclasses

import pytest

from asusrouter.modules.network.enums import ARNetworkBackend
from asusrouter.modules.network.handle import ARNetworkHandle


class TestARNetworkHandle:
    """Tests for ARNetworkHandle."""

    def test_requires_backend(self) -> None:
        """The backend is the only required field; the rest default empty."""

        handle = ARNetworkHandle(backend=ARNetworkBackend.SDN)
        assert handle.backend is ARNetworkBackend.SDN
        assert handle.sdn_idx is None
        assert handle.ap_prefix is None
        assert handle.ap_idx is None
        assert handle.units == ()

    def test_carries_fields(self) -> None:
        """Provided SDN and legacy fields are stored."""

        handle = ARNetworkHandle(
            backend=ARNetworkBackend.LEGACY,
            sdn_idx=2,
            ap_prefix="wl",
            ap_idx=1,
            units=((0, None), (1, 2)),
        )
        assert handle.sdn_idx == 2
        assert handle.units == ((0, None), (1, 2))

    def test_frozen(self) -> None:
        """The handle is immutable."""

        handle = ARNetworkHandle(backend=ARNetworkBackend.SDN)
        with pytest.raises(dataclasses.FrozenInstanceError):
            handle.sdn_idx = 5  # type: ignore[misc]

    def test_equal_by_value(self) -> None:
        """Handles with the same fields compare equal and hash alike."""

        a = ARNetworkHandle(backend=ARNetworkBackend.SDN, sdn_idx=1)
        b = ARNetworkHandle(backend=ARNetworkBackend.SDN, sdn_idx=1)
        assert a == b
        assert hash(a) == hash(b)
