"""Tests for the SSID tools."""

from __future__ import annotations

from asusrouter.tools.identifiers import Ssid
from asusrouter.tools.security import REDACTED, ARSecurityLevel, ARSensitive

_SSID = "my-network"


def test_is_sensitive() -> None:
    """SSID is sensitive with a DEFAULT reveal level, not maskable."""

    ssid = Ssid(_SSID)
    assert isinstance(ssid, ARSensitive)
    assert ssid.reveal_level is ARSecurityLevel.DEFAULT
    assert ssid.maskable is False


def test_value_and_str() -> None:
    """The raw value is accessible and shown by str."""

    ssid = Ssid(_SSID)
    assert ssid.value == _SSID
    assert str(ssid) == _SSID
    assert repr(ssid) == f"Ssid({_SSID!r})"


def test_from_value() -> None:
    """from_value returns the same instance if already an Ssid."""

    ssid = Ssid(_SSID)
    assert Ssid.from_value(ssid) is ssid
    assert Ssid.from_value(_SSID) == ssid


def test_from_value_safe() -> None:
    """from_value_safe returns None for missing or empty values."""

    ssid = Ssid(_SSID)
    assert Ssid.from_value_safe(ssid) is ssid
    assert Ssid.from_value_safe(_SSID) == ssid
    assert Ssid.from_value_safe(None) is None
    assert Ssid.from_value_safe("") is None


def test_default_mask() -> None:
    """Not maskable, so mask falls back to the redaction marker."""

    assert Ssid(_SSID).mask() is REDACTED


def test_equality_and_hash() -> None:
    """Equality against SSID and string, hashing by value."""

    ssid = Ssid(_SSID)
    assert ssid == Ssid(_SSID)
    assert ssid == _SSID
    assert (ssid == 42) is False
    assert hash(ssid) == hash(_SSID)
