"""Tests for the AiMesh capability decoding."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.aimesh import capability as capability_module
from asusrouter.modules.aimesh.capability import (
    ARAiMeshFeature,
    is_fully_decoded,
    translate_features,
)


class TestTranslateFeatures:
    """Tests for translate_features."""

    def test_decodes_bits(self) -> None:
        """Set bits across indices resolve to features."""

        # idx 1 (led) value 5 -> bits 0,2; idx 4 value 1 -> bit 0 (usb)
        features = translate_features({"1": "5", "4": "1"})

        assert features == frozenset(
            {
                ARAiMeshFeature.CENTRAL_LED,
                ARAiMeshFeature.LED_ON_OFF,
                ARAiMeshFeature.USB,
            }
        )

    def test_mlo_bits(self) -> None:
        """High rc_support bits (mlo) decode correctly."""

        # bits 20 (mlo_bh) + 21 (mlo_fh)
        features = translate_features({"4": str((1 << 20) | (1 << 21))})

        assert ARAiMeshFeature.MLO_BH in features
        assert ARAiMeshFeature.MLO_FH in features

    @pytest.mark.parametrize(
        "capability",
        ["x", {}, {"99": "1"}, {"1": ""}, {"1": "x"}],
        ids=["not_dict", "empty", "unknown_index", "blank", "non_int"],
    )
    def test_empty(self, capability: Any) -> None:
        """Bad or unmapped input yields no features."""

        assert translate_features(capability) == frozenset()

    def _capture_warnings(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> list[list[int]]:
        """Patch the logger to capture warned bit lists."""

        capability_module._reported_unknown_bits.clear()
        warned: list[list[int]] = []
        monkeypatch.setattr(
            capability_module._LOGGER,
            "warning",
            lambda *a, **k: warned.append(a[1]),
        )
        return warned

    def test_unknown_bits_warn_per_bit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Each distinct unmapped bit is warned about only once."""

        warned = self._capture_warnings(monkeypatch)

        # idx 1 bit 7; idx 2 fully mapped (no warn)
        translate_features({"1": "128", "2": "1"})
        # idx 1 bit 7 already reported -> no warn
        translate_features({"1": "128"})
        # idx 5 (lacp): bits 3,5 -> all new
        translate_features({"5": str((1 << 3) | (1 << 5))})
        # idx 5: bits 3,7 -> only 7 is new
        translate_features({"5": str((1 << 3) | (1 << 7))})
        # idx 5: bit 3 -> nothing new
        translate_features({"5": str(1 << 3)})

        assert warned == [[7], [3, 5], [7]]

    def test_acknowledged_bits_not_warned(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Known-unparseable bits do not warn; genuinely new ones do."""

        warned = self._capture_warnings(monkeypatch)

        # idx 4 value with only acknowledged unknown bits -> no warn
        translate_features({"4": "62498685"})
        # idx 4 with a non-acknowledged bit 30 -> warns only that one
        translate_features({"4": str(1 << 30)})

        assert warned == [[30]]


class TestIsFullyDecoded:
    """Tests for is_fully_decoded."""

    @pytest.mark.parametrize(
        ("key", "value", "expected"),
        [
            ("2", "1", True),
            ("5", "1", True),
            ("1", "127", True),
            ("1", "128", False),
            ("99", "1", False),
            ("4", "x", False),
        ],
        ids=[
            "reboot_full",
            "lacp_full",
            "led_all_known",
            "led_unknown_bit7",
            "unknown_index",
            "non_int",
        ],
    )
    def test_cases(self, key: str, value: str, expected: bool) -> None:
        """A value is fully decoded only when every set bit is mapped."""

        assert is_fully_decoded(key, value) is expected
