"""Tests for the MAC address tools."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.identifiers.mac import (
    ERROR_MAC_BYTE,
    ERROR_MAC_INT,
    ERROR_MAC_STR,
    ERROR_MAC_UNSUPPORTED_TYPE,
)
from asusrouter.tools.security import configure_key

CORRECT_MAC = "aa:bb:cc:dd:ee:ff"
CORRECT_MAC_HEX = CORRECT_MAC.replace(":", "")
CORRECT_MAC_BYTES = bytes.fromhex(CORRECT_MAC_HEX)
CORRECT_MAC_INT = int.from_bytes(CORRECT_MAC_BYTES, "big")
CORRECT_MAC_AS_ASUS = CORRECT_MAC.upper()


def test_from_instance() -> None:
    """Test initialization from an instance."""

    instance = MacAddress.from_value(CORRECT_MAC)

    assert MacAddress(instance) == instance
    assert MacAddress.from_value(instance) == instance


def test_from_bytes() -> None:
    """Test initialization from bytes."""

    assert str(MacAddress.from_value(CORRECT_MAC_BYTES)) == CORRECT_MAC
    assert str(MacAddress(CORRECT_MAC_BYTES)) == CORRECT_MAC


@pytest.mark.parametrize(
    "value",
    [
        bytes.fromhex("00"),
        bytes.fromhex("aabbff"),
    ],
)
def test_from_bytes_fail(value: bytes) -> None:
    """Test initialization from invalid bytes."""

    with pytest.raises(ValueError, match=ERROR_MAC_BYTE):
        MacAddress.from_value(value)

    with pytest.raises(ValueError, match=ERROR_MAC_BYTE):
        MacAddress(value)


@pytest.mark.parametrize(
    ("value", "result"),
    [
        (CORRECT_MAC_INT, CORRECT_MAC),
        (123, "00:00:00:00:00:7b"),
        ("  123  ", "00:00:00:00:00:7b"),
    ],
)
def test_from_int(value: int, result: str) -> None:
    """Test initialization from an integer."""

    instance = MacAddress(value)
    assert str(instance) == result
    assert MacAddress.from_value(value) == instance


@pytest.mark.parametrize(
    "value",
    [
        -1,
        1 << 48,
    ],
)
def test_from_int_fail(value: int) -> None:
    """Test initialization from an invalid integer."""

    with pytest.raises(ValueError, match=ERROR_MAC_INT):
        MacAddress.from_value(value)

    with pytest.raises(ValueError, match=ERROR_MAC_INT):
        MacAddress(value)


@pytest.mark.parametrize(
    ("value", "result"),
    [
        (CORRECT_MAC, CORRECT_MAC),
        ("AA-BB-CC-DD-EE-FF", CORRECT_MAC),
        ("aabb.ccdd.eeff", CORRECT_MAC),
        ("AABBCCDDEEFF", CORRECT_MAC),
        (f"  {CORRECT_MAC}  ", CORRECT_MAC),
    ],
)
def test_from_string(value: str, result: str) -> None:
    """Test initialization from various string formats."""

    instance = MacAddress(value)
    assert str(instance) == result
    assert MacAddress.from_value(value) == instance


@pytest.mark.parametrize(
    "value",
    [
        "not a mac",
        "ff:aa:bb:cc:dd:ee:ff",
    ],
)
def test_from_string_fail(value: str) -> None:
    """Test initialization from invalid string formats."""

    with pytest.raises(ValueError, match=ERROR_MAC_STR):
        MacAddress.from_value(value)

    with pytest.raises(ValueError, match=ERROR_MAC_STR):
        MacAddress(value)


@pytest.mark.parametrize(
    "value",
    [
        None,
        object(),
    ],
)
def test_from_unsupported(value: Any) -> None:
    """Test initialization from unsupported types."""

    with pytest.raises(ValueError, match=ERROR_MAC_UNSUPPORTED_TYPE):
        MacAddress.from_value(value)

    with pytest.raises(ValueError, match=ERROR_MAC_UNSUPPORTED_TYPE):
        MacAddress(value)


def test_from_value_safe() -> None:
    """Test safe mode returns MacAddress for valid input and None otherwise."""

    assert MacAddress.from_value_safe(CORRECT_MAC) == MacAddress(CORRECT_MAC)
    assert MacAddress.from_value_safe(None) is None
    assert MacAddress.from_value_safe(object()) is None


@pytest.mark.parametrize(
    ("value", "result"),
    [
        (CORRECT_MAC, CORRECT_MAC_AS_ASUS),
        ("00:aa:11:bb:22:cc", "00:AA:11:BB:22:CC"),
    ],
)
def test_to_asus(value: str, result: str) -> None:
    """Test conversion to ASUS format."""

    instance = MacAddress.from_value(value)
    assert instance.as_asus() == result


def test_to_bytes() -> None:
    """Test conversion to bytes."""

    instance = MacAddress.from_value(CORRECT_MAC)
    assert instance.to_bytes() == CORRECT_MAC_BYTES


def test_to_int() -> None:
    """Test conversion to integer."""

    instance = MacAddress.from_value(CORRECT_MAC)
    assert instance.to_int() == CORRECT_MAC_INT


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("00:00:00:00:00:00", "02:00:00:00:00:00"),
        ("44:00:00:00:00:00", "46:00:00:00:00:00"),
        ("99:00:00:00:00:00", "9a:00:00:00:00:00"),
        ("ff:00:00:00:00:00", "fe:00:00:00:00:00"),
    ],
)
def test_set_locally_administered(value: str, expected: str) -> None:
    """Test setting the locally-administered bit."""

    instance = MacAddress.from_value(value)
    instance.set_locally_administered()
    assert str(instance) == expected


def test_repr() -> None:
    """Test string representation."""

    instance = MacAddress.from_value(CORRECT_MAC)
    assert repr(instance) == CORRECT_MAC


@pytest.mark.parametrize(
    ("value", "result"),
    [
        (CORRECT_MAC, True),
        ("00:00:00:00:00:00", False),
        (MacAddress(CORRECT_MAC), True),
        (MacAddress("00:00:00:00:00:00"), False),
    ],
)
def test_eq(value: Any, result: bool) -> None:
    """Test equality comparison."""

    instance = MacAddress.from_value(CORRECT_MAC)
    assert (instance == value) is result


def test_eq_returns_notimplemented_for_uncomparable() -> None:
    """Test equality comparison with uncomparable types."""

    mac = MacAddress.from_value(CORRECT_MAC)

    class Uncomparable:
        pass

    other = Uncomparable()

    # Direct unbound call returns the NotImplemented sentinel
    assert MacAddress.__eq__(mac, other) is NotImplemented

    # Public comparison uses NotImplemented
    assert (mac == other) is False
    assert (other == mac) is False


def test_hash() -> None:
    """Test hash function."""

    instance = MacAddress.from_value(CORRECT_MAC)
    assert hash(instance) == hash(CORRECT_MAC_BYTES)


def test_mask_deterministic_and_local() -> None:
    """Masked MAC is deterministic and locally-administered."""

    configure_key(b"A" * 32)

    mac = MacAddress.from_value(CORRECT_MAC)
    masked = mac.mask()

    # Masked value differs from the original
    assert masked != mac

    # Deterministic for the same key
    assert masked == mac.mask()

    # Locally-administered bit set, multicast bit cleared
    b0 = masked.to_bytes()[0]
    assert (b0 & 0x02) != 0
    assert (b0 & 0x01) == 0


def test_mask_depends_on_key() -> None:
    """Masked MAC changes with the masking key."""

    mac = MacAddress.from_value(CORRECT_MAC)

    configure_key(b"A" * 32)
    m1 = mac.mask()

    configure_key(b"B" * 32)
    m2 = mac.mask()

    assert m1 != m2
