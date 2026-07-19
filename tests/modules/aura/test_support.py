"""Tests for the aura support helpers."""

from __future__ import annotations

from types import SimpleNamespace

from asusrouter.modules.aura.support import (
    aura_supported,
    night_mode_supported,
)
from asusrouter.modules.support.flag import ARSupportType


def _identity(*, aura: bool = True, night: bool = False) -> SimpleNamespace:
    """Build a fake identity exposing an Aura support map."""

    return SimpleNamespace(
        support={
            ARSupportType.AURA: aura,
            ARSupportType.AURA_NIGHT_MODE: night,
        }
    )


class TestAuraSupported:
    """Tests for aura_supported."""

    def test_supported(self) -> None:
        """An Aura-capable identity reports supported."""

        assert aura_supported(_identity(aura=True)) is True

    def test_unsupported(self) -> None:
        """An identity without Aura reports unsupported."""

        assert aura_supported(_identity(aura=False)) is False

    def test_no_identity(self) -> None:
        """A missing identity reports unsupported."""

        assert aura_supported(None) is False


class TestNightModeSupported:
    """Tests for night_mode_supported."""

    def test_supported(self) -> None:
        """A night-mode-capable identity reports supported."""

        assert night_mode_supported(_identity(night=True)) is True

    def test_unsupported(self) -> None:
        """An identity without night mode reports unsupported."""

        assert night_mode_supported(_identity(night=False)) is False

    def test_no_identity(self) -> None:
        """A missing identity reports unsupported."""

        assert night_mode_supported(None) is False
