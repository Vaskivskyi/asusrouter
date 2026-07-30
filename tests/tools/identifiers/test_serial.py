"""Tests for serial number tools."""

from __future__ import annotations

import pytest

from asusrouter.tools.identifiers import Serial
from asusrouter.tools.security import REDACTED, ARSecurityLevel, render

_SERIAL = "R2FAKE000000ABC"


class TestSerial:
    """Tests for the Serial type."""

    def test_value(self) -> None:
        """The raw serial is kept as given."""

        assert Serial(_SERIAL).value == _SERIAL
        assert str(Serial(_SERIAL)) == _SERIAL
        assert _SERIAL in repr(Serial(_SERIAL))

    def test_is_a_hardware_identifier(self) -> None:
        """A serial is levelled like the other hardware identifiers."""

        assert Serial.reveal_level is ARSecurityLevel.REASONABLE
        assert Serial.maskable is True

    def test_mask_is_deterministic(self) -> None:
        """The same serial always yields the same stand-in."""

        masked = Serial(_SERIAL).mask()

        assert masked != _SERIAL
        assert str(masked).startswith("sn-")
        assert masked == Serial(_SERIAL).mask()

    @pytest.mark.parametrize(
        ("level", "expected"),
        [
            (ARSecurityLevel.STRICT, "redacted"),
            (ARSecurityLevel.SANITIZED, "masked"),
            (ARSecurityLevel.REASONABLE, "raw"),
            (ARSecurityLevel.UNSAFE, "raw"),
        ],
    )
    def test_render(self, level: ARSecurityLevel, expected: str) -> None:
        """Redacted below sanitized, masked in between, raw from its level."""

        rendered = render(Serial(_SERIAL), level)

        if expected == "redacted":
            assert rendered is REDACTED
        elif expected == "masked":
            assert str(rendered).startswith("sn-")
        else:
            assert rendered == _SERIAL

    def test_from_value(self) -> None:
        """An existing serial is passed through, anything else wrapped."""

        serial = Serial(_SERIAL)

        assert Serial.from_value(serial) is serial
        assert Serial.from_value(_SERIAL) == serial

    @pytest.mark.parametrize("value", [None, ""])
    def test_from_value_safe_empty(self, value: str | None) -> None:
        """A missing or empty serial is no serial at all."""

        assert Serial.from_value_safe(value) is None

    def test_from_value_safe(self) -> None:
        """A real value is wrapped, an existing one passed through."""

        serial = Serial(_SERIAL)

        assert Serial.from_value_safe(serial) is serial
        assert Serial.from_value_safe(_SERIAL) == serial

    def test_equality(self) -> None:
        """Serials compare by value, including against a plain string."""

        assert Serial(_SERIAL) == Serial(_SERIAL)
        assert Serial(_SERIAL) == _SERIAL
        assert Serial(_SERIAL) != Serial("other")
        assert Serial(_SERIAL) != 42
        assert hash(Serial(_SERIAL)) == hash(_SERIAL)
