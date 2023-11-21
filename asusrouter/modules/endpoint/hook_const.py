"""Constants for hook endpoint module."""

# Network

from asusrouter.modules.connection import ConnectionState, ConnectionStatus
from asusrouter.modules.endpoint.wan import AsusDualWAN
from asusrouter.modules.ip_address import read_dns_ip_address, read_ip_address_type
from asusrouter.modules.openvpn import AsusOVPNServer
from asusrouter.modules.wireguard import AsusWireGuardServer
from asusrouter.tools.converters import (
    safe_bool,
    safe_int,
    safe_list_csv,
    safe_list_from_string,
    safe_timestamp_to_utc,
)

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

MAP_OVPN_SERVER_388 = (
    ("vpn_server_unit", "unit", safe_int),
    ("vpn_serverx_dns", "response_to_dns", safe_bool),
    ("vpn_server_port", "port", safe_int),
    ("vpn_server_tls_keysize", "tls_keysize", safe_int),
    ("vpn_server_if", "interface"),
    ("vpn_server_proto", "protocol"),
    ("vpn_server_pdns", "advertise_dns", safe_bool),
    ("vpn_server_cipher", "cipher"),
    ("vpn_server_digest", "digest"),
    ("vpn_server_comp", "compression"),
    ("vpn_server_igncrt", "password_only", safe_bool),
    ("vpn_server_crypt", "auth_mode"),
    ("vpn_server_hmac", "hmac"),
    ("vpn_server_sn", "subnet"),
    ("vpn_server_nm", "netmask"),
    ("vpn_server_dhcp", "dhcp", safe_bool),
    ("vpn_server_r1", "server_r1"),
    ("vpn_server_r2", "server_r2"),
    ("vpn_server_local", "address"),
    ("vpn_server_remote", "remote_address"),
    ("vpn_server_plan", "allow_lan", safe_bool),
    ("vpn_server_rgw", "allow_wan", safe_bool),
    ("vpn_server_reneg", "tls_reneg", safe_int),
    ("vpn_server_ccd", "client_specific_config", safe_bool),
    ("vpn_server_c2c", "client_to_client", safe_bool),
    ("vpn_server_ccd_excl", "allow_specific_clients", safe_bool),
    ("vpn_server_ccd_val", "specific_clients"),
    ("vpn_serverx_clientlist", "clients"),
    ("VPNServer_enable", "state", [safe_int, AsusOVPNServer]),
)

MAP_SPEEDTEST = (
    ("ookla_state", "state", safe_int),
    ("ookla_speedtest_get_history", "history"),
    ("ookla_speedtest_get_servers", "servers"),
    ("ookla_speedtest_get_result", "result"),
)

MAP_WAN = (
    ("get_wan_unit", "unit", safe_int),
    ("link_internet", "link", [safe_int, ConnectionStatus]),
    ("link_wan", "link_0", [safe_int, ConnectionState]),
    ("link_wan1", "link_1", [safe_int, ConnectionState]),
    ("wans_mode", "dualwan_mode", AsusDualWAN),
    ("wans_dualwan", "dualwan_priority", safe_list_from_string),
    ("bond_wan", "aggregation_state", safe_bool),
    ("wanports_bond", "aggregation_ports", safe_list_from_string),
)

MAP_WAN_ITEM = (
    ("auxstate_t", "auxstate", [safe_int, ConnectionStatus]),
    ("primary", "primary", safe_bool),
    ("proto", "protocol", read_ip_address_type),
    ("realip_ip", "real_ip"),
    ("realip_state", "real_ip_state", safe_bool),
    ("state_t", "state", [safe_int, ConnectionStatus]),
    ("sbstate_t", "bstate", [safe_int, ConnectionStatus]),
)

MAP_WAN_ITEM_X = (
    ("dns", "dns", read_dns_ip_address),
    ("expires", "expires", safe_int),
    ("gateway", "gateway"),
    ("ipaddr", "ip_address"),
    ("lease", "lease", safe_int),
    ("netmask", "mask"),
)

MAP_WIREGUARD_SERVER = (
    ("wgs_enable", "state", [safe_int, AsusWireGuardServer]),
    ("wgs_lanaccess", "lan_access", safe_bool),
    ("wgs_addr", "address"),
    ("wgs_port", "port", safe_int),
    ("wgs_dns", "dns", safe_bool),
    ("wgs_nat6", "nat6", safe_bool),
    ("wgs_psk", "psk", safe_bool),
    ("wgs_alive", "keep_alive", safe_int),
    ("wgs_priv", "private_key"),
    ("wgs_pub", "public_key"),
    ("get_wgsc_status", "status"),
)

MAP_WIREGUARD_CLIENT = (
    ("enable", "enabled", safe_bool),
    ("name", "name"),
    ("addr", "address"),
    ("aips", "allowed_ips", safe_list_csv),
    ("caips", "client_allowed_ips", safe_list_csv),
)

MAP_VPNC_WIREGUARD = (
    ("enable", "state", safe_bool),
    ("nat", "nat", safe_bool),
    ("priv", "private_key"),
    ("addr", "address"),
    ("dns", "dns", safe_bool),
    ("mtu", "mtu", safe_int),
    ("ppub", "public_key"),
    ("psk", "psk"),
    ("aips", "allowed_ips", safe_list_csv),
    ("ep_addr", "endpoint_address"),
    ("ep_port", "endpoint_port", safe_int),
    ("alive", "keep_alive", safe_int),
)
