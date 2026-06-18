"""Constants for the VPN endpoint module."""

from __future__ import annotations

from asusrouter.tools.converters import safe_datetime
from asusrouter.tools.converters_v2.raw import raw_to_int

MAP_OVPN_CLIENT = [
    ("REMOTE", "remote", None),
    ("Updated", "datetime", safe_datetime),
    ("TUN/TAP read bytes", "tun_tap_read", raw_to_int),
    ("TUN/TAP write bytes", "tun_tap_write", raw_to_int),
    ("TCP/UDP read bytes", "tcp_udp_read", raw_to_int),
    ("TCP/UDP write bytes", "tcp_udp_write", raw_to_int),
    ("Auth read bytes", "auth_read", raw_to_int),
    ("pre-compress bytes", "pre_compress", raw_to_int),
    ("post-compress bytes", "post_compress", raw_to_int),
    ("pre-decompress bytes", "pre_decompress", raw_to_int),
    ("post-decompress bytes", "post_decompress", raw_to_int),
]

MAP_OVPN_SERVER = [
    ("CLIENT_LIST", "client_list"),
    ("ROUTING_TABLE", "routing_table"),
]
