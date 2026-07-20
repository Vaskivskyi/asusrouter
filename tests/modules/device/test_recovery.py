"""Tests for the device identity recovery."""

from __future__ import annotations

import pytest

from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.device.recovery import (
    _wifi_generation_from_model,
    recover_support,
)
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.modules.wifi import (
    ARWiFiBand,
    ARWiFiGeneration,
    ARWiFiMultiBand,
)

_S = ARSupportType
_G = ARWiFiGeneration
_MB = ARWiFiMultiBand


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("RT-AC66U", _G.WIFI_5),
        ("RT-AC5300", _G.WIFI_5),
        ("RT-AX88U", _G.WIFI_6),
        ("GT-AXE16000", _G.WIFI_6),
        ("GT-BE98", _G.WIFI_7),
        # No marker in the name
        ("ZenWiFi-XT8", _G.UNKNOWN),
        (None, _G.UNKNOWN),
        ("", _G.UNKNOWN),
    ],
)
def test_wifi_generation_from_model(
    model: str | None, expected: ARWiFiGeneration
) -> None:
    """The WiFi generation is read from the model name marker."""

    assert _wifi_generation_from_model(model) is expected


def _identity(
    *,
    model: str | None = None,
    bands: int = 0,
    generation: ARWiFiGeneration = _G.UNKNOWN,
    multiband: ARWiFiMultiBand = _MB.UNKNOWN,
) -> ARDeviceIdentity:
    identity = ARDeviceIdentity()
    identity._model = model
    identity._wifi = {
        band: unit for unit, band in enumerate(list(ARWiFiBand)[1 : bands + 1])
    }
    identity._support = {
        _S.WIFI_GENERATION: generation,
        _S.WIFI_MULTIBAND: multiband,
    }
    return identity


class TestRecoverSupport:
    """Tests for recover_support."""

    def test_recovers_both_from_legacy_data(self) -> None:
        """A legacy device recovers generation from model and band count."""

        identity = _identity(model="RT-AC66U", bands=2)

        recover_support(identity)

        assert identity.support[_S.WIFI_GENERATION] is _G.WIFI_5
        assert identity.support[_S.WIFI_MULTIBAND] is _MB.DUALBAND

    def test_keeps_fetched_values(self) -> None:
        """A real fetched value is never overwritten by recovery."""

        identity = _identity(
            model="RT-AC66U",
            bands=2,
            generation=_G.WIFI_7,
            multiband=_MB.TRIBAND,
        )

        recover_support(identity)

        assert identity.support[_S.WIFI_GENERATION] is _G.WIFI_7
        assert identity.support[_S.WIFI_MULTIBAND] is _MB.TRIBAND

    def test_unrecoverable_stays_unknown(self) -> None:
        """No model marker and no bands leaves both unknown."""

        identity = _identity(model="ZenWiFi-XT8", bands=0)

        recover_support(identity)

        assert identity.support[_S.WIFI_GENERATION] is _G.UNKNOWN
        assert identity.support[_S.WIFI_MULTIBAND] is _MB.UNKNOWN
