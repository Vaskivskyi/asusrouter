"""IP address tools."""

from __future__ import annotations

from ipaddress import (
    IPv4Address,
    IPv4Interface,
    IPv6Address,
    IPv6Interface,
    ip_address,
    ip_interface,
)
from typing import Any, Final

from asusrouter.tools.security import ARSecurityLevel, ARSensitive, hmac_digest

IP_VERSION_V4: Final[int] = 4
IP_LENGTH_BYTES_V4: Final[int] = 4
IP_LENGTH_BYTES_V6: Final[int] = 16

ERROR_IP_BYTES: Final[str] = (
    "IP address must be 4 bytes (IPv4) or 16 bytes (IPv6)"
)
ERROR_IP_INT: Final[str] = "IP address integer out of range"
ERROR_IP_STR: Final[str] = "Invalid IP address string"
ERROR_IP_UNSUPPORTED_TYPE: Final[str] = "Unsupported IP address type"


class IpAddress(ARSensitive):
    """IP address representation supporting IPv4 and IPv6."""

    __slots__ = ("_addr",)

    reveal_level = ARSecurityLevel.REASONABLE
    maskable = True

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

    def mask(self) -> IpAddress:
        """Return a deterministic pseudo-address of the same version."""

        size = (
            IP_LENGTH_BYTES_V4
            if self._addr.version == IP_VERSION_V4
            else IP_LENGTH_BYTES_V6
        )
        return IpAddress(hmac_digest(self._addr.packed)[:size])

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


class IpInterface(ARSensitive):
    """IP interface (address with a network prefix, e.g. `10.55.0.1/24`)."""

    __slots__ = ("_iface",)

    reveal_level = ARSecurityLevel.REASONABLE
    maskable = True

    def __init__(self, iface: Any) -> None:
        """Initialize IpInterface.

        If an IPv4Interface or IPv6Interface is passed, it is used directly;
        otherwise the universal conversion is performed.
        """

        # Fast-path for stdlib interface types
        if isinstance(iface, IPv4Interface | IPv6Interface):
            self._iface = iface
            return

        self._iface = type(self)._to_iface(iface)

    @classmethod
    def _to_iface(cls, value: Any) -> IPv4Interface | IPv6Interface:
        """Convert supported values to an IPv4Interface or IPv6Interface.

        Supported inputs:
        - IpInterface -> returns underlying interface
        - IPv4Interface / IPv6Interface -> used directly
        - IpAddress / IPv4Address / IPv6Address -> host address (`/32`, `/128`)
        - str: `address` or `address/prefix` notation
        """

        # Already an IpInterface instance
        if isinstance(value, cls):
            return value._iface

        # Stdlib interface types
        if isinstance(value, IPv4Interface | IPv6Interface):
            return value

        # Address types collapse to a host interface
        if isinstance(value, IpAddress):
            value = str(value)
        if isinstance(value, IPv4Address | IPv6Address):
            value = str(value)

        if isinstance(value, str):
            try:
                return ip_interface(value.strip())
            except ValueError:
                raise ValueError(ERROR_IP_STR)

        raise ValueError(f"{ERROR_IP_UNSUPPORTED_TYPE}: {type(value)!r}")

    @classmethod
    def from_value(cls, value: Any) -> IpInterface:
        """Create an IpInterface from various representations."""

        if isinstance(value, cls):
            return value

        return cls(cls._to_iface(value))

    @classmethod
    def from_value_safe(cls, value: Any) -> IpInterface | None:
        """Create an IpInterface, or None if the value cannot be parsed."""

        try:
            return cls.from_value(value)
        except ValueError:
            return None

    @property
    def version(self) -> int:
        """Return the IP version (4 or 6)."""

        return self._iface.version

    @property
    def ip(self) -> IpAddress:
        """Return the host address without the prefix."""

        return IpAddress(self._iface.ip)

    @property
    def prefixlen(self) -> int:
        """Return the network prefix length."""

        return self._iface.network.prefixlen

    def mask(self) -> IpInterface:
        """Return a pseudo-interface: masked address, original prefix."""

        return IpInterface(f"{self.ip.mask()}/{self.prefixlen}")

    def __str__(self) -> str:
        """Return the `address/prefix` representation."""

        return str(self._iface)

    def __repr__(self) -> str:
        """Return the `address/prefix` representation."""

        return str(self._iface)

    def __eq__(self, other: object) -> bool:
        """Return whether two IP interfaces are equal."""

        if isinstance(other, IpInterface):
            return self._iface == other._iface
        try:
            other_obj = type(self).from_value(other)
        except ValueError:
            return NotImplemented
        return self._iface == other_obj._iface

    def __hash__(self) -> int:
        """Return the hash of the IP interface."""

        return hash(self._iface)


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


def read_ip_interface_list(value: Any) -> list[IpInterface]:
    """Read a comma/whitespace-separated string into a list of IP interfaces.

    Returns every interface that parses; an empty list when none do.
    """

    if not isinstance(value, str):
        return []
    return [
        iface
        for part in value.replace(",", " ").split()
        if (iface := IpInterface.from_value_safe(part)) is not None
    ]
