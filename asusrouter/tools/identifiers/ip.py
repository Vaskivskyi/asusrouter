"""IP address tools."""

from __future__ import annotations

from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Any, Final

ERROR_IP_BYTES: Final[str] = (
    "IP address must be 4 bytes (IPv4) or 16 bytes (IPv6)"
)
ERROR_IP_INT: Final[str] = "IP address integer out of range"
ERROR_IP_STR: Final[str] = "Invalid IP address string"
ERROR_IP_UNSUPPORTED_TYPE: Final[str] = "Unsupported IP address type"


class IpAddress:
    """IP address representation supporting IPv4 and IPv6."""

    __slots__ = ("_addr",)

    def __init__(self, ip: Any) -> None:
        """Initialize IpAddress.

        If an IPv4Address or IPv6Address is passed, it is used directly;
        otherwise the universal conversion is performed.
        """

        # Fast-path for stdlib address types
        if isinstance(ip, IPv4Address | IPv6Address):
            self._addr = ip
            return

        self._addr = type(self)._to_addr(ip)

    @classmethod
    def _to_addr(cls, value: Any) -> IPv4Address | IPv6Address:
        """Convert supported values to an IPv4Address or IPv6Address.

        Supported inputs:
        - IpAddress -> returns underlying address
        - IPv4Address / IPv6Address -> used directly
        - bytes/bytearray: 4 bytes (IPv4) or 16 bytes (IPv6)
        - int: in [0, 2**128)
        - str: any valid IPv4 or IPv6 notation
        """

        # Already an IpAddress instance
        if isinstance(value, cls):
            return value._addr

        # Stdlib address types
        if isinstance(value, IPv4Address | IPv6Address):
            return value

        # Bytes-like
        if isinstance(value, bytes | bytearray):
            if len(value) not in (4, 16):
                raise ValueError(ERROR_IP_BYTES)
            return ip_address(bytes(value))

        # Integer
        if isinstance(value, int):
            try:
                return ip_address(value)
            except ValueError:
                raise ValueError(ERROR_IP_INT)

        # String
        if isinstance(value, str):
            try:
                return ip_address(value.strip())
            except ValueError:
                raise ValueError(ERROR_IP_STR)

        raise ValueError(f"{ERROR_IP_UNSUPPORTED_TYPE}: {type(value)!r}")

    @classmethod
    def from_value(cls, value: Any) -> IpAddress:
        """Create an IpAddress from various representations.

        Returns either the same instance (if passed an IpAddress) or a new
        IpAddress constructed from the parsed representation.
        """

        if isinstance(value, cls):
            return value

        parsed = cls._to_addr(value)
        return cls(parsed)

    @classmethod
    def from_value_safe(cls, value: Any) -> IpAddress | None:
        """Create an IpAddress from various representations.

        Returns a new IpAddress if the input is valid, or None if the
        provided value cannot be parsed as an IP address.
        """

        try:
            return cls.from_value(value)
        except ValueError:
            return None

    @property
    def version(self) -> int:
        """Return the IP version (4 or 6)."""

        return self._addr.version

    @property
    def is_private(self) -> bool:
        """Return whether the address is a private address."""

        return self._addr.is_private

    @property
    def is_loopback(self) -> bool:
        """Return whether the address is a loopback address."""

        return self._addr.is_loopback

    def to_bytes(self) -> bytes:
        """Return the packed bytes (4 bytes for IPv4, 16 bytes for IPv6)."""

        return self._addr.packed

    def to_int(self) -> int:
        """Return the integer representation of the IP address."""

        return int(self._addr)

    def __str__(self) -> str:
        """Return the string representation of the IP address."""

        return str(self._addr)

    def __repr__(self) -> str:
        """Return the string representation of the IP address."""

        return str(self._addr)

    def __eq__(self, other: object) -> bool:
        """Return whether two IP addresses are equal."""

        if isinstance(other, IpAddress):
            return self._addr == other._addr
        try:
            other_obj = type(self).from_value(other)
        except ValueError:
            return NotImplemented
        return self._addr == other_obj._addr

    def __hash__(self) -> int:
        """Return the hash of the IP address."""

        return hash(self._addr)


def read_ip_list(value: Any) -> list[IpAddress]:
    """Read a whitespace-separated string into a list of IP addresses.

    Returns every address that parses; an empty list when none do.
    """

    if not isinstance(value, str):
        return []
    return [
        ip
        for part in value.split()
        if (ip := IpAddress.from_value_safe(part)) is not None
    ]
