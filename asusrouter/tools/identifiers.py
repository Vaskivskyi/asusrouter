"""Identifier tools."""

from __future__ import annotations

import re
from typing import Any, Final

from asusrouter.tools.converters import clean_string, safe_int

MAC_CLEAN_RE: Final[re.Pattern[str]] = re.compile(r"[^0-9a-fA-F]")
MAC_LENGTH_BYTES: Final[int] = 6
MAC_LENGTH_STR: Final[int] = 12

ERROR_MAC_BYTE: Final[str] = "MAC address must be exactly 6 bytes"
ERROR_MAC_INT: Final[str] = "MAC address must be a 48-bit integer"
ERROR_MAC_STR: Final[str] = "Invalid MAC address string"
ERROR_MAC_UNSUPPORTED_TYPE: Final[str] = "Unsupported MAC address type"


class MacAddress:
    """MAC address representation."""

    __slots__ = ("_bytes",)

    def __init__(self, mac: Any) -> None:
        """Initialize MacAddress.

        If bytes/bytearray of length 6 are passed, they are used directly;
        otherwise the universal conversion is performed.
        """

        # Fast-path for raw bytes
        if isinstance(mac, bytes | bytearray):
            if len(mac) != MAC_LENGTH_BYTES:
                raise ValueError(ERROR_MAC_BYTE)
            self._bytes = bytes(mac)
            return

        # Use universal conversion
        self._bytes = type(self)._to_bytes(mac)

    @classmethod
    def _to_bytes(cls, value: Any) -> bytes:
        """Convert supported values to 6-byte canonical MAC representation.

        Supported inputs:
        - MacAddress -> returns underlying bytes
        - bytes/bytearray (length 6)
        - int in [0, 2**48)
        - str with separators or plain hex
        """

        # Already a MacAddress instance
        if isinstance(value, cls):
            return value._bytes

        # Bytes-like
        if isinstance(value, bytes | bytearray):
            if len(value) != MAC_LENGTH_BYTES:
                raise ValueError(ERROR_MAC_BYTE)
            return bytes(value)

        # Integer-compatible
        vint = safe_int(value)
        if isinstance(vint, int):
            if vint < 0 or vint >= (1 << 48):
                raise ValueError(ERROR_MAC_INT)
            return int.to_bytes(vint, 6, "big")

        # String-compatible
        vstr = clean_string(value)
        if isinstance(vstr, str):
            cleaned = MAC_CLEAN_RE.sub("", vstr).lower()
            if len(cleaned) != MAC_LENGTH_STR or not all(
                c in "0123456789abcdef" for c in cleaned
            ):
                raise ValueError(ERROR_MAC_STR)
            return bytes.fromhex(cleaned)

        raise ValueError(f"{ERROR_MAC_UNSUPPORTED_TYPE}: {type(value)!r}")

    @classmethod
    def from_value(cls, value: Any) -> MacAddress:
        """Create a MacAddress from various representations.

        Returns either the same instance (if passed a MacAddress) or a new
        MacAddress constructed from the canonical 6-byte representation.
        """

        if isinstance(value, cls):
            return value

        # Use the shared parser to obtain bytes, then construct using the
        # bytes fast-path in __init__.
        parsed = cls._to_bytes(value)
        return cls(parsed)

    def as_asus(self) -> str:
        """Return the MAC address in ASUS format.

        The default Asus format is XX:XX:XX:XX:XX:XX.
        """

        return str(self).upper()

    def to_bytes(self) -> bytes:
        """Return the MAC address as bytes."""

        return self._bytes

    def to_int(self) -> int:
        """Return the MAC address as a 48-bit integer."""

        return int.from_bytes(self._bytes, "big")

    def set_locally_administered(self) -> None:
        """Transform the MAC address to a locally-administered address.

        For this, the locally-administered bit (bit 1) is set to 1 and the
        multicast bit (LSB) is cleared (set to 0).
        """

        _bytes = bytearray(self._bytes)
        _bytes[0] = (_bytes[0] & ~0x01) | 0x02
        self._bytes = bytes(_bytes)

    def __str__(self) -> str:
        """Return the string representation of the MAC address."""

        hx = self._bytes.hex()
        pairs = [hx[i : i + 2] for i in range(0, 12, 2)]
        return ":".join(pairs)

    def __repr__(self) -> str:
        """Return the string representation of the MAC address."""

        return str(self)

    def __eq__(self, other: object) -> bool:
        """Return whether two MAC addresses are equal."""

        if isinstance(other, MacAddress):
            return self._bytes == other._bytes
        try:
            other_obj = MacAddress.from_value(other)
        except ValueError:
            return NotImplemented
        return self._bytes == other_obj._bytes

    def __hash__(self) -> int:
        """Return the hash of the MAC address."""

        return hash(self._bytes)
