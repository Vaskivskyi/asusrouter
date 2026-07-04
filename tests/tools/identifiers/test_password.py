"""Tests for the password tools."""

from __future__ import annotations

from asusrouter.tools.identifiers import Password
from asusrouter.tools.security import (
    REDACTED,
    REDACTED_STR,
    ARSecurityLevel,
    ARSensitive,
)

_PASSWORD = "s3cr3t"


def test_is_sensitive() -> None:
    """Password is sensitive with an UNSAFE reveal level, not maskable."""

    password = Password(_PASSWORD)
    assert isinstance(password, ARSensitive)
    assert password.reveal_level is ARSecurityLevel.UNSAFE
    assert password.maskable is False


def test_value_accessible_but_str_redacted() -> None:
    """Raw value only via value; str and repr never leak it."""

    password = Password(_PASSWORD)
    assert password.value == _PASSWORD
    assert str(password) == REDACTED_STR
    assert repr(password) == f"Password({REDACTED_STR})"
    assert _PASSWORD not in repr(password)


def test_from_value() -> None:
    """from_value returns the same instance if already a Password."""

    password = Password(_PASSWORD)
    assert Password.from_value(password) is password
    assert Password.from_value(_PASSWORD) == password


def test_from_value_safe() -> None:
    """from_value_safe returns None for missing or empty values."""

    password = Password(_PASSWORD)
    assert Password.from_value_safe(password) is password
    assert Password.from_value_safe(_PASSWORD) == password
    assert Password.from_value_safe(None) is None
    assert Password.from_value_safe("") is None


def test_default_mask() -> None:
    """Not maskable, so mask falls back to the redaction marker."""

    assert Password(_PASSWORD).mask() is REDACTED


def test_equality_and_hash() -> None:
    """Equality against Password and string, hashing by value."""

    password = Password(_PASSWORD)
    assert password == Password(_PASSWORD)
    assert password == _PASSWORD
    assert (password == 42) is False
    assert hash(password) == hash(_PASSWORD)
