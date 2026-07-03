"""Constants for hook endpoint module."""

from __future__ import annotations

from asusrouter.modules.openvpn import AsusOVPNServer
from asusrouter.modules.wireguard import AsusWireGuardServer
from asusrouter.tools.converters import safe_list_csv
from asusrouter.tools.converters_v2.raw import raw_to_bool, raw_to_int

MAP_OVPN_SERVER_388 = (
    ("vpn_server_unit", "unit", raw_to_int),
    ("vpn_serverx_dns", "response_to_dns", raw_to_bool),
    ("vpn_server_port", "port", raw_to_int),
    ("vpn_server_tls_keysize", "tls_keysize", raw_to_int),
    ("vpn_server_if", "interface"),
    ("vpn_server_proto", "protocol"),
    ("vpn_server_pdns", "advertise_dns", raw_to_bool),
    ("vpn_server_cipher", "cipher"),
    ("vpn_server_digest", "digest"),
    ("vpn_server_comp", "compression"),
    ("vpn_server_igncrt", "password_only", raw_to_bool),
    ("vpn_server_crypt", "auth_mode"),
    ("vpn_server_hmac", "hmac"),
    ("vpn_server_sn", "subnet"),
    ("vpn_server_nm", "netmask"),
    ("vpn_server_dhcp", "dhcp", raw_to_bool),
    ("vpn_server_r1", "server_r1"),
    ("vpn_server_r2", "server_r2"),
    ("vpn_server_local", "address"),
    ("vpn_server_remote", "remote_address"),
    ("vpn_server_plan", "allow_lan", raw_to_bool),
    ("vpn_server_rgw", "allow_wan", raw_to_bool),
    ("vpn_server_reneg", "tls_reneg", raw_to_int),
    ("vpn_server_ccd", "client_specific_config", raw_to_bool),
    ("vpn_server_c2c", "client_to_client", raw_to_bool),
    ("vpn_server_ccd_excl", "allow_specific_clients", raw_to_bool),
    ("vpn_server_ccd_val", "specific_clients"),
    ("vpn_serverx_clientlist", "clients"),
    ("VPNServer_enable", "state", [raw_to_int, AsusOVPNServer]),
)

MAP_WIREGUARD_SERVER = (
    ("wgs_enable", "state", [raw_to_int, AsusWireGuardServer]),
    ("wgs_lanaccess", "lan_access", raw_to_bool),
    ("wgs_addr", "address"),
    ("wgs_port", "port", raw_to_int),
    ("wgs_dns", "dns", raw_to_bool),
    ("wgs_nat6", "nat6", raw_to_bool),
    ("wgs_psk", "psk", raw_to_bool),
    ("wgs_alive", "keep_alive", raw_to_int),
    ("wgs_priv", "private_key"),
    ("wgs_pub", "public_key"),
    ("get_wgsc_status", "status"),
)

MAP_WIREGUARD_CLIENT = (
    ("enable", "enabled", raw_to_bool),
    ("name", "name"),
    ("addr", "address"),
    ("aips", "allowed_ips", safe_list_csv),
    ("caips", "client_allowed_ips", safe_list_csv),
)

MAP_VPNC_WIREGUARD = (
    ("enable", "state", raw_to_bool),
    ("nat", "nat", raw_to_bool),
    ("priv", "private_key"),
    ("addr", "address"),
    ("dns", "dns", raw_to_bool),
    ("mtu", "mtu", raw_to_int),
    ("ppub", "public_key"),
    ("psk", "psk"),
    ("aips", "allowed_ips", safe_list_csv),
    ("ep_addr", "endpoint_address"),
    ("ep_port", "endpoint_port", raw_to_int),
    ("alive", "keep_alive", raw_to_int),
)
