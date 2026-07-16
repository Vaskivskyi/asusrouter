"""Tests for the security level enum."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.tools.security import ARSecurityLevel


class TestARSecurityLevel:
    """Tests for the ARSecurityLevel enum."""

    @pytest.mark.parametrize(
        ("name", "value"),
        [
            ("UNKNOWN", -999),
            ("STRICT", 0),
            ("DEFAULT", 1),
            ("SANITIZED", 5),
            ("REASONABLE", 7),
            ("UNSAFE", 9),
        ],
    )
    def test_members(self, name: str, value: int) -> None:
        """Test that the members have the expected values."""

        member = getattr(ARSecurityLevel, name)
        assert member.value == value

    def test_ordering(self) -> None:
        """Test that the levels are correctly ordered."""

        assert ARSecurityLevel.STRICT < ARSecurityLevel.DEFAULT
        assert ARSecurityLevel.DEFAULT < ARSecurityLevel.SANITIZED
        assert ARSecurityLevel.SANITIZED < ARSecurityLevel.REASONABLE
        assert ARSecurityLevel.REASONABLE < ARSecurityLevel.UNSAFE

    def test_lookup(self) -> None:
        """Test member lookup by value and name."""

        assert ARSecurityLevel(1) is ARSecurityLevel.DEFAULT
        assert ARSecurityLevel["REASONABLE"] is ARSecurityLevel.REASONABLE

    def test_unique(self) -> None:
        """Test that all values are unique."""

        values = [member.value for member in ARSecurityLevel]
        assert len(values) == len(set(values))

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (ARSecurityLevel.DEFAULT, ARSecurityLevel.DEFAULT),
            (1, ARSecurityLevel.DEFAULT),
            ("1", ARSecurityLevel.DEFAULT),
            ("5.0", ARSecurityLevel.SANITIZED),
            (7, ARSecurityLevel.REASONABLE),
            (861, ARSecurityLevel.UNKNOWN),
            ("sanitized", ARSecurityLevel.SANITIZED),
            ("REASONABLE", ARSecurityLevel.REASONABLE),
            (None, ARSecurityLevel.UNKNOWN),
            ("unknown-name", ARSecurityLevel.UNKNOWN),
            (object(), ARSecurityLevel.UNKNOWN),
        ],
    )
    def test_from_value(self, value: Any, expected: ARSecurityLevel) -> None:
        """Test the from_value method."""

        assert ARSecurityLevel.from_value(value) is expected
