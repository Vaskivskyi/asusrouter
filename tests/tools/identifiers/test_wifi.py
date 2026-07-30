"""Tests for the WiFi interface identifier."""

from __future__ import annotations

import pytest

from asusrouter.tools.identifiers.wifi import WiFiInterface


class TestFromValue:
    """Parsing an interface from a value."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("0.2", WiFiInterface(0, 2)),
            ("0 2", WiFiInterface(0, 2)),
            ("wl0.2", WiFiInterface(0, 2)),
            ("1 1", WiFiInterface(1, 1)),
            ("2", WiFiInterface(2, 0)),
            (WiFiInterface(1, 3), WiFiInterface(1, 3)),
        ],
    )
    def test_parses(self, value: object, expected: WiFiInterface) -> None:
        """Both formats (and a `wl` prefix) parse to the same interface."""

        assert WiFiInterface.from_value(value) == expected

    @pytest.mark.parametrize("value", ["", "a.b", "0.1.2", "wl"])
    def test_invalid_raises(self, value: str) -> None:
        """An unparseable value raises."""

        with pytest.raises(ValueError, match="Invalid WiFi interface"):
            WiFiInterface.from_value(value)


class TestFromValueSafe:
    """The non-raising constructor."""

    def test_valid(self) -> None:
        """A valid value parses."""

        assert WiFiInterface.from_value_safe("0 2") == WiFiInterface(0, 2)

    @pytest.mark.parametrize("value", [None, "", "bad"])
    def test_invalid_returns_none(self, value: object) -> None:
        """A missing or unparseable value returns None."""

        assert WiFiInterface.from_value_safe(value) is None


def test_str_is_canonical() -> None:
    """The string form is always `unit.subunit`."""

    assert str(WiFiInterface.from_value("0 2")) == "0.2"


def test_hashable() -> None:
    """Frozen interfaces are hashable and value-equal."""

    assert WiFiInterface(0, 2) in {WiFiInterface(0, 2)}
