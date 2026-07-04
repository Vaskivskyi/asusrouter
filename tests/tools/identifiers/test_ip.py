"""Tests for the IP address tools."""

from __future__ import annotations

from ipaddress import IPv4Address, IPv6Address
import re
from typing import Any

import pytest

from asusrouter.tools.identifiers import IpAddress
from asusrouter.tools.identifiers.ip import (
    ERROR_IP_BYTES,
    ERROR_IP_INT,
    ERROR_IP_STR,
    ERROR_IP_UNSUPPORTED_TYPE,
    read_ip_list,
)
from asusrouter.tools.security import configure_key

CORRECT_IPV4 = "192.168.1.1"
CORRECT_IPV4_BYTES = IPv4Address(CORRECT_IPV4).packed
CORRECT_IPV4_INT = int(IPv4Address(CORRECT_IPV4))

CORRECT_IPV6 = "2001:db8::1"
CORRECT_IPV6_CANONICAL = str(IPv6Address(CORRECT_IPV6))
CORRECT_IPV6_BYTES = IPv6Address(CORRECT_IPV6).packed
CORRECT_IPV6_INT = int(IPv6Address(CORRECT_IPV6))


def test_from_instance() -> None:
    """Test initialization from an existing IpAddress instance."""

    instance = IpAddress.from_value(CORRECT_IPV4)

    assert IpAddress(instance) == instance
    assert IpAddress.from_value(instance) is instance


@pytest.mark.parametrize(
    ("addr", "expected"),
    [
        (IPv4Address(CORRECT_IPV4), CORRECT_IPV4),
        (IPv6Address(CORRECT_IPV6), CORRECT_IPV6_CANONICAL),
    ],
)
def test_from_stdlib(addr: IPv4Address | IPv6Address, expected: str) -> None:
    """Test initialization and from_value from stdlib address types."""

    # __init__ fast-path
    assert str(IpAddress(addr)) == expected
    # from_value goes through _to_addr stdlib branch
    assert str(IpAddress.from_value(addr)) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (CORRECT_IPV4_BYTES, CORRECT_IPV4),
        (CORRECT_IPV6_BYTES, CORRECT_IPV6_CANONICAL),
        (bytearray(CORRECT_IPV4_BYTES), CORRECT_IPV4),
    ],
)
def test_from_bytes(value: bytes | bytearray, expected: str) -> None:
    """Test initialization from valid bytes."""

    assert str(IpAddress.from_value(value)) == expected
    assert str(IpAddress(value)) == expected


@pytest.mark.parametrize(
    "value",
    [
        bytes(3),
        bytes(5),
        bytes(17),
    ],
)
def test_from_bytes_fail(value: bytes) -> None:
    """Test initialization from bytes of invalid length."""

    with pytest.raises(ValueError, match=re.escape(ERROR_IP_BYTES)):
        IpAddress.from_value(value)

    with pytest.raises(ValueError, match=re.escape(ERROR_IP_BYTES)):
        IpAddress(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (CORRECT_IPV4_INT, CORRECT_IPV4),
        (CORRECT_IPV6_INT, CORRECT_IPV6_CANONICAL),
        (0, "0.0.0.0"),
        (2**32 - 1, "255.255.255.255"),
        (2**32, str(IPv6Address(2**32))),
    ],
)
def test_from_int(value: int, expected: str) -> None:
    """Test initialization from a valid integer."""

    assert str(IpAddress.from_value(value)) == expected
    assert str(IpAddress(value)) == expected


@pytest.mark.parametrize(
    "value",
    [
        -1,
        2**128,
    ],
)
def test_from_int_fail(value: int) -> None:
    """Test initialization from an out-of-range integer."""

    with pytest.raises(ValueError, match=ERROR_IP_INT):
        IpAddress.from_value(value)

    with pytest.raises(ValueError, match=ERROR_IP_INT):
        IpAddress(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (CORRECT_IPV4, CORRECT_IPV4),
        (f"  {CORRECT_IPV4}  ", CORRECT_IPV4),
        ("::1", "::1"),
        (CORRECT_IPV6, CORRECT_IPV6_CANONICAL),
    ],
)
def test_from_string(value: str, expected: str) -> None:
    """Test initialization from valid string representations."""

    instance = IpAddress(value)
    assert str(instance) == expected
    assert IpAddress.from_value(value) == instance


@pytest.mark.parametrize(
    "value",
    [
        "not an ip",
        "999.999.999.999",
        "192.168.1",
    ],
)
def test_from_string_fail(value: str) -> None:
    """Test initialization from invalid string representations."""

    with pytest.raises(ValueError, match=ERROR_IP_STR):
        IpAddress.from_value(value)

    with pytest.raises(ValueError, match=ERROR_IP_STR):
        IpAddress(value)


@pytest.mark.parametrize(
    "value",
    [
        None,
        object(),
    ],
)
def test_from_unsupported(value: Any) -> None:
    """Test initialization from unsupported types."""

    with pytest.raises(ValueError, match=ERROR_IP_UNSUPPORTED_TYPE):
        IpAddress.from_value(value)

    with pytest.raises(ValueError, match=ERROR_IP_UNSUPPORTED_TYPE):
        IpAddress(value)


def test_from_value_safe() -> None:
    """Test safe mode returns IpAddress for valid input and None otherwise."""

    assert IpAddress.from_value_safe(CORRECT_IPV4) == IpAddress(CORRECT_IPV4)
    assert IpAddress.from_value_safe(None) is None
    assert IpAddress.from_value_safe(object()) is None


@pytest.mark.parametrize(
    ("value", "expected_version"),
    [
        (CORRECT_IPV4, 4),
        (CORRECT_IPV6, 6),
    ],
)
def test_version(value: str, expected_version: int) -> None:
    """Test IP version property."""

    assert IpAddress.from_value(value).version == expected_version


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("192.168.1.1", True),
        ("8.8.8.8", False),
        ("fc00::1", True),
        ("2606:4700::1", False),
    ],
)
def test_is_private(value: str, expected: bool) -> None:
    """Test is_private property."""

    assert IpAddress.from_value(value).is_private == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("127.0.0.1", True),
        ("192.168.1.1", False),
        ("::1", True),
        ("::2", False),
    ],
)
def test_is_loopback(value: str, expected: bool) -> None:
    """Test is_loopback property."""

    assert IpAddress.from_value(value).is_loopback == expected


def test_to_bytes() -> None:
    """Test to_bytes returns packed representation."""

    assert IpAddress.from_value(CORRECT_IPV4).to_bytes() == CORRECT_IPV4_BYTES
    assert IpAddress.from_value(CORRECT_IPV6).to_bytes() == CORRECT_IPV6_BYTES


def test_to_int() -> None:
    """Test to_int returns integer representation."""

    assert IpAddress.from_value(CORRECT_IPV4).to_int() == CORRECT_IPV4_INT
    assert IpAddress.from_value(CORRECT_IPV6).to_int() == CORRECT_IPV6_INT


def test_repr() -> None:
    """Test repr matches str."""

    instance = IpAddress.from_value(CORRECT_IPV4)
    assert repr(instance) == CORRECT_IPV4


@pytest.mark.parametrize(
    ("value", "result"),
    [
        (CORRECT_IPV4, True),
        ("8.8.8.8", False),
        (IpAddress(CORRECT_IPV4), True),
        (IpAddress("8.8.8.8"), False),
    ],
)
def test_eq(value: Any, result: bool) -> None:
    """Test equality comparison."""

    instance = IpAddress.from_value(CORRECT_IPV4)
    assert (instance == value) is result


def test_eq_returns_notimplemented_for_uncomparable() -> None:
    """Test equality comparison with uncomparable types returns NotImplemented.

    An Uncomparable object raises ValueError in from_value, so __eq__ must
    return NotImplemented to let Python fall back to the other side.
    """

    ip = IpAddress.from_value(CORRECT_IPV4)

    class Uncomparable:
        pass

    other = Uncomparable()

    # Direct unbound call returns the NotImplemented sentinel
    assert IpAddress.__eq__(ip, other) is NotImplemented

    # Public comparison uses NotImplemented
    assert (ip == other) is False
    assert (other == ip) is False


def test_hash() -> None:
    """Test hash matches the stdlib address hash."""

    instance = IpAddress.from_value(CORRECT_IPV4)
    assert hash(instance) == hash(IPv4Address(CORRECT_IPV4))


class TestReadIpList:
    """Tests for read_ip_list."""

    def test_single(self) -> None:
        """A single address is read into a one-item list."""

        result = read_ip_list(CORRECT_IPV4)
        assert result == [IpAddress.from_value(CORRECT_IPV4)]

    def test_multiple(self) -> None:
        """Whitespace-separated addresses are all read."""

        result = read_ip_list(f"{CORRECT_IPV4}  {CORRECT_IPV6}")
        assert result == [
            IpAddress.from_value(CORRECT_IPV4),
            IpAddress.from_value(CORRECT_IPV6),
        ]

    def test_skips_invalid(self) -> None:
        """Invalid tokens are skipped, valid ones kept."""

        result = read_ip_list(f"{CORRECT_IPV4} nope")
        assert result == [IpAddress.from_value(CORRECT_IPV4)]

    @pytest.mark.parametrize("value", ["", "   ", "nope", None, 42, []])
    def test_empty(self, value: Any) -> None:
        """Unparseable or non-string input returns an empty list."""

        assert read_ip_list(value) == []


class TestIpMask:
    """Tests for deterministic IP masking."""

    def test_mask_ipv4(self) -> None:
        """Masked IPv4 is deterministic and same-version."""

        configure_key(b"A" * 32)

        ip = IpAddress.from_value(CORRECT_IPV4)
        masked = ip.mask()

        assert masked.version == 4
        assert masked != ip
        assert masked == ip.mask()

    def test_mask_ipv6(self) -> None:
        """Masked IPv6 is deterministic and same-version."""

        configure_key(b"A" * 32)

        ip = IpAddress.from_value(CORRECT_IPV6)
        masked = ip.mask()

        assert masked.version == 6
        assert masked != ip
        assert masked == ip.mask()

    def test_mask_depends_on_key(self) -> None:
        """Masked IP changes with the masking key."""

        ip = IpAddress.from_value(CORRECT_IPV4)

        configure_key(b"A" * 32)
        m1 = ip.mask()

        configure_key(b"B" * 32)
        m2 = ip.mask()

        assert m1 != m2
