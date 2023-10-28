"""IP address module."""

import re
from enum import Enum
from typing import Optional

from asusrouter.tools.converters import clean_string


class IPAddressType(str, Enum):
    """IP address type class."""

    DHCP = "dhcp"
    PPPOE = "pppoe"
    PPTP = "pptp"
    STATIC = "static"
    UNKNOWN = "unknown"


def read_ip_address_type(data: Optional[str]) -> IPAddressType:
    """Read IP address type from data string."""

    data = clean_string(data)

    if data:
        data = data.lower()

    # Find the IP address type in the IPAddressType enum by value
    for ip_address_type in IPAddressType:
        if ip_address_type.value == data:
            return ip_address_type

    # Some other values to convert
    if data == "manual":
        return IPAddressType.STATIC

    # If the IP address type is not found, return the UNKNOWN type
    return IPAddressType.UNKNOWN


def read_dns_ip_address(data: str) -> list[str]:
    """Read DNS record and return the list of IP addresses."""

    # Regex to find each IP address in a string of IP addresses
    regex = r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    # Find all IP addresses in the string
    matches = re.findall(regex, data)

    return matches
