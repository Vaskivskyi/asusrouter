"""Constants for hook endpoint module."""

# Network

from asusrouter.modules.ip_address import read_dns_ip_address, read_ip_address_type
from asusrouter.tools.converters import safe_bool, safe_int

MAP_NETWORK: dict[str, str] = {
    "INTERNET": "wan",
    "INTERNET1": "usb",
    "WIRED": "wired",
    "BRIDGE": "bridge",
    "WIRELESS0": "2ghz",
    "WIRELESS1": "5ghz",
    "WIRELESS2": "5ghz2",
    "WIRELESS3": "6ghz",
    "LACP1": "lacp1",
    "LACP2": "lacp2",
}

MAP_WAN = (
    ("wanstate", "state"),
    ("wansbstate", "bstate"),
    ("wanauxstate", "aux"),
    ("autodet_state"),
    ("autodet_auxstate"),
    ("wanlink_status", "status", safe_bool),
    ("wanlink_type", "ip_type", read_ip_address_type),
    ("wanlink_ipaddr", "ip_address"),
    ("wanlink_netmask", "mask"),
    ("wanlink_gateway", "gateway"),
    ("wanlink_dns", "dns", read_dns_ip_address),
    ("wanlink_lease", "lease", safe_int),
    ("wanlink_expires", "expires", safe_int),
    ("is_private_subnet", "private_subnet", safe_int),
    ("wanlink_xtype", "xtype", read_ip_address_type),
    ("wanlink_xipaddr", "xip"),
    ("wanlink_xnetmask", "xmask"),
    ("wanlink_xgateway", "xgateway"),
    ("wanlink_xdns", "xdns", read_dns_ip_address),
    ("wanlink_xlease", "xlease", safe_int),
    ("wanlink_xexpires", "xexpires", safe_int),
)
