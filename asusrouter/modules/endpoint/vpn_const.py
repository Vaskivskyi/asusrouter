"""Constants for the VPN endpoint module."""

from asusrouter.tools.converters import safe_datetime, safe_int

MAP_OVPN_CLIENT = [
    ("REMOTE", "remote", None),
    ("Updated", "datetime", safe_datetime),
    ("TUN/TAP read bytes", "tun_tap_read", safe_int),
    ("TUN/TAP write bytes", "tun_tap_write", safe_int),
    ("TCP/UDP read bytes", "tcp_udp_read", safe_int),
    ("TCP/UDP write bytes", "tcp_udp_write", safe_int),
    ("Auth read bytes", "auth_read", safe_int),
    ("pre-compress bytes", "pre_compress", safe_int),
    ("post-compress bytes", "post_compress", safe_int),
    ("pre-decompress bytes", "pre_decompress", safe_int),
    ("post-decompress bytes", "post_decompress", safe_int),
]

MAP_OVPN_SERVER = [
    ("CLIENT_LIST", "client_list"),
    ("ROUTING_TABLE", "routing_table"),
]
