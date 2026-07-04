"""Tests for the hostname tools."""

from __future__ import annotations

from asusrouter.tools.identifiers import Hostname
from asusrouter.tools.security import (
    ARSecurityLevel,
    ARSensitive,
    configure_key,
)

_HOST = "router.example.com"
_IP = "192.168.1.1"


def test_is_sensitive() -> None:
    """Hostname is sensitive at REASONABLE and maskable."""

    host = Hostname(_HOST)
    assert isinstance(host, ARSensitive)
    assert host.reveal_level is ARSecurityLevel.REASONABLE
    assert host.maskable is True


def test_value_and_str() -> None:
    """The raw value is accessible and shown by str."""

    host = Hostname(_HOST)
    assert host.value == _HOST
    assert str(host) == _HOST
    assert repr(host) == f"Hostname({_HOST!r})"


def test_from_value() -> None:
    """from_value returns the same instance if already a Hostname."""

    host = Hostname(_HOST)
    assert Hostname.from_value(host) is host
    assert Hostname.from_value(_HOST) == host


def test_from_value_safe() -> None:
    """from_value_safe returns None for missing or empty values."""

    host = Hostname(_HOST)
    assert Hostname.from_value_safe(host) is host
    assert Hostname.from_value_safe(_HOST) == host
    assert Hostname.from_value_safe(None) is None
    assert Hostname.from_value_safe("") is None


def test_mask_deterministic() -> None:
    """Masked hostname is a deterministic pseudo-host."""

    configure_key(b"A" * 32)

    host = Hostname(_HOST)
    masked = host.mask()

    assert isinstance(masked, Hostname)
    assert masked != host
    assert masked.value.startswith("host-")
    assert masked == host.mask()


def test_mask_depends_on_key() -> None:
    """Masked hostname changes with the masking key."""

    host = Hostname(_IP)

    configure_key(b"A" * 32)
    m1 = host.mask()

    configure_key(b"B" * 32)
    m2 = host.mask()

    assert m1 != m2


def test_equality_and_hash() -> None:
    """Equality against Hostname and string, hashing by value."""

    host = Hostname(_HOST)
    assert host == Hostname(_HOST)
    assert host == _HOST
    assert (host == 42) is False
    assert hash(host) == hash(_HOST)
