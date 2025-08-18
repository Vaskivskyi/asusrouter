"""Tests for the identifiers tools."""

from typing import Any

import pytest

from asusrouter.tools.identifiers import (
    ERROR_MAC_BYTE,
    ERROR_MAC_INT,
    ERROR_MAC_STR,
    ERROR_MAC_UNSUPPORTED_TYPE,
    MacAddress,
)

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
    ("value"),
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
    ("value"),
    [
        -1,
        1 << 48,
    ],
)
def test_from_int_fail(value: int) -> None:
    """Test initialization from an invalid integer."""

    with pytest.raises(ValueError, match=ERROR_MAC_INT):
        MacAddress.from_value(value)


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
    ("value"),
    [
        "not a mac",
        "ff:aa:bb:cc:dd:ee:ff",
    ],
)
def test_from_string_fail(value: str) -> None:
    """Test initialization from invalid string formats."""

    with pytest.raises(ValueError, match=ERROR_MAC_STR):
        MacAddress.from_value(value)


@pytest.mark.parametrize(
    ("value"),
    [
        None,
        object(),
    ],
)
def test_from_unsupported(value: Any) -> None:
    """Test initialization from unsupported types."""

    with pytest.raises(ValueError, match=ERROR_MAC_UNSUPPORTED_TYPE):
        MacAddress.from_value(value)


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
