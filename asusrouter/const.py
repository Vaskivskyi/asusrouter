"""AsusRouter constants module"""

from enum import Enum
from typing import Any

from asusrouter.dataclass import Key, SearchKey
from asusrouter.util.converters import (
    bool_from_any,
    bool_or_int,
    datetime_from_str,
    exists_or_not,
    float_from_str,
    int_from_str,
    ovpn_remote_fom_str,
    service_support,
    time_from_delta,
)


### ENUMS
class Merge(str, Enum):
    """Merge enumerator for getting data"""

    ALL = "all"
    ANY = "any"


### API VALUES
AR_USER_AGENT = "asusrouter--DUTUtil-"
AR_API = [
    "Model_Name",
    "AiHOMEAPILevel",
    "Httpd_AiHome_Ver",
]
AR_ERROR_CODE = {
    "authorization": 2,
    "credentials": 3,
    "try_again": 7,
    "logout": 8,
}

### VALUES
ACTION_MODE = "action_mode"
AIMESH = "aimesh"
APPLY = "apply"
APPOBJ = "appobj"
AUTHORIZATION = "authorization"
BLOCK = "block"
BOOTTIME = "boottime"
BRIDGE = "bridge"
CLIENTS = "clients"
CLIENTS_HISTORIC = "clients_historic"
COMMAND = "command"
CONNECTION_TYPE = "connection_type"
CPU = "cpu"
CPU_USAGE = "cpu_usage"
CREDENTIALS = "credentials"
DATA = "data"
DEVICEMAP = "devicemap"
DEVICES = "devices"
DIAG = "diag"
DISABLE = "disable"
DHCP = "dhcp"
ENDPOINTS = "endpoints"
ERROR_STATUS = "error_status"
ERRNO = "errno"
FIRMWARE = "firmware"
FREE = "free"
GUEST = "guest"
GWLAN = "gwlan"
HOOK = "hook"
HTTP = "http"
HTTPS = "https"
INFO = "info"
IP = "ip"
ISO = "iso"
LACP = "lacp"
LAN = "lan"
LED = "led"
LED_VAL = "led_val"
LEDG = "ledg"
LIGHT = "light"
LINK_RATE = "link_rate"
LOAD_AVG = "load_avg"
LOGIN = "login"
LOGOUT = "logout"
MAC = "mac"
MAIN = "main"
MEM = "mem"
MEMORY_USAGE = "memory_usage"
MONITOR = "monitor"
NAME = "name"
NETDEV = "netdev"
NETWORK = "network"
NETWORKMAPD = "networkmapd"
NODE = "node"
NPMCLIENT = "npmclient"
NVRAM = "nvram"
NVRAM_GET = "nvram_get"
ONBOARDING = "onboarding"
ONLINE = "online"
PARENTAL_CONTROL = "parental_control"
PORT = "port"
PORTS = "ports"
QTN = "qtn"
RAM = "ram"
RGB = "rgb"
RIP = "rip"
RSSI = "rssi"
RULES = "rules"
RX = "rx"
SERVICE_COMMAND = "rc_service"
SERVICE_MODIFY = "modify"
SERVICE_REPLY = "run_service"
SERVICE_SET_LED = "start_ctrl_led"
SIM = "sim"
STATE = "state"
STATUS = "status"
SUCCESS = "success"
SYS = "sys"
SYSINFO = "sysinfo"
TEMPERATURE = "temperature"
TIME = "time"
TIMEMAP = "timemap"
TIMESTAMP = "timestamp"
TOTAL = "total"
TRY_AGAIN = "try_again"
TX = "tx"
TYPE = "type"
UNKNOWN = "unknown"
UPDATE_CLIENTS = "update_clients"
USAGE = "usage"
USED = "used"
USB = "usb"
VPN = "vpn"
VPN_CLIENT = "vpn_client"
VPN_SERVER = "vpn_server"
WAN = "wan"
WANLINK_STATE = "wanlink_state"
WIRED = "wired"
WLAN = "wlan"
WLAN_2GHZ = "2ghz"
WLAN_5GHZ = "5ghz"
WLAN_5GHZ2 = "5ghz2"
WLAN_6GHZ = "6ghz"

### ASUS DATA TYPES
ETHERNET_PORTS = "ethernet_ports"
PORT_STATUS = "port_status"

### Keys & delimiters
KEY_PARENTAL_CONTROL_MAC = "MULTIFILTER_MAC"
KEY_PARENTAL_CONTROL_NAME = "MULTIFILTER_DEVICENAME"
KEY_PARENTAL_CONTROL_STATE = "MULTIFILTER_ALL"
KEY_PARENTAL_CONTROL_TIMEMAP = "MULTIFILTER_MACFILTER_DAYTIME_V2"
KEY_PARENTAL_CONTROL_TYPE = "MULTIFILTER_ENABLE"

DELIMITER_PARENTAL_CONTROL_ITEM = "&#62"


### ENDPOINTS
ENDPOINT_LOGIN = "login.cgi"
ENDPOINT_LOGOUT = "Logout.asp"

ENDPOINT = {
    APPLY: "apply.cgi",
    COMMAND: "applyapp.cgi",
    DEVICEMAP: "ajax_status.xml",
    ETHERNET_PORTS: "ajax_ethernet_ports.asp",
    FIRMWARE: "detect_firmware.asp",
    HOOK: "appGet.cgi",
    LEDG: "set_ledg.cgi",
    # NETWORKMAPD: "update_networkmapd.asp",
    ONBOARDING: "ajax_onboarding.asp",
    PORT_STATUS: "get_port_status.cgi",
    RGB: "light_effect.html",
    STATE: "state.js",
    SYSINFO: "ajax_sysinfo.asp",
    TEMPERATURE: "ajax_coretmp.asp",
    UPDATE_CLIENTS: "update_clients.asp",
    VPN: "ajax_vpn_status.asp",
}

ENDHOOKS: dict[str, Any] = {
    DEVICES: [("get_clientlist", "")],
    LIGHT: [
        (NVRAM_GET, LED_VAL),
    ],
    MAIN: [
        (CPU_USAGE, APPOBJ),
        (MEMORY_USAGE, APPOBJ),
        (NETDEV, APPOBJ),
        (WANLINK_STATE, APPOBJ),
    ],
    NVRAM: None,
    PARENTAL_CONTROL: [
        (NVRAM_GET, KEY_PARENTAL_CONTROL_MAC),
        (NVRAM_GET, KEY_PARENTAL_CONTROL_NAME),
        (NVRAM_GET, KEY_PARENTAL_CONTROL_STATE),
        (NVRAM_GET, KEY_PARENTAL_CONTROL_TIMEMAP),
        (NVRAM_GET, KEY_PARENTAL_CONTROL_TYPE),
    ],
}
ENDPOINT_ARGS = {
    PORT_STATUS: {
        MAC: f"{NODE}_{MAC}",
    },
}

### History-dependent values in the monitor to be removed to prevent errors
HD_DATA: tuple[tuple[str, ...], ...] = (
    (MAIN, CPU),
    (MAIN, NETWORK),
)

### REQUIREMENTS
# Don't create loops
CONST_REQUIRE_MONITOR = {
    WLAN: MAIN,
}
MONITOR_REQUIRE_CONST = {
    NVRAM: WLAN,
}

### ASUS NUMERICS, RANGES & MAPS

# Map of the parameters for connected device
# value_to_find: [where_to_search, method to convert]
# List is sorted by importance with the most important first
MAP_CONNECTED_DEVICE: dict[str, list[SearchKey]] = {
    "connected_since": [
        SearchKey("wlConnectTime", time_from_delta),
    ],
    CONNECTION_TYPE: [
        SearchKey(CONNECTION_TYPE),
        SearchKey("isWL", int_from_str),
    ],
    GUEST: [
        SearchKey(GUEST),
        SearchKey("isGN", int_from_str),
    ],
    "internet_mode": [
        SearchKey("internetMode"),
    ],
    "internet_state": [
        SearchKey("internetState", bool_from_any),
    ],
    IP: [
        SearchKey(IP),
    ],
    "ip_method": [
        SearchKey("ipMethod"),
    ],
    MAC: [
        SearchKey(MAC),
    ],
    NAME: [
        SearchKey("nickName"),
        SearchKey(NAME),
        SearchKey(MAC),
    ],
    NODE: [
        SearchKey(NODE),
    ],
    ONLINE: [
        SearchKey(ONLINE),
        SearchKey("isOnline", bool_from_any),
    ],
    RSSI: [
        SearchKey(RSSI, int_from_str),
    ],
    "rx_speed": [
        SearchKey("curRx", float_from_str),
    ],
    "tx_speed": [
        SearchKey("curTx", float_from_str),
    ],
}
MAP_CPU: tuple[Key, ...] = (Key(TOTAL), Key(USAGE, USED))
MAP_IDENTITY: tuple[Key, ...] = (
    Key("serial_no", "serial"),
    Key("label_mac", MAC),
    Key("lan_hwaddr", "lan_mac"),
    Key("wan_hwaddr", "wan_mac"),
    Key("productid", "model"),
    Key("firmver", "fw_major"),
    Key("buildno", "fw_minor"),
    Key("extendno", "fw_build"),
    Key("rc_support", "services", method=service_support),
    Key("ss_support", "services", method=service_support),
    Key(LED_VAL, LED, method=exists_or_not),
)
MAP_NETWORK: tuple[Key, ...] = (
    Key("INTERNET", WAN),
    Key("INTERNET1", USB),
    Key("WIRED", WIRED),
    Key("BRIDGE", BRIDGE),
    Key("WIRELESS0", WLAN_2GHZ),
    Key("WIRELESS1", WLAN_5GHZ),
    Key("WIRELESS2", WLAN_5GHZ2),
    Key("WIRELESS3", WLAN_6GHZ),
    Key("LACP1", f"{LACP}1"),
    Key("LACP2", f"{LACP}2"),
)
MAP_NVRAM = {
    WLAN: [
        SearchKey("wl{}_auth_mode_x"),
        SearchKey("wl{}_bw"),
        SearchKey("wl{}_channel"),
        SearchKey("wl{}_chanspec"),
        SearchKey("wl{}_closed", bool_from_any),
        SearchKey("wl{}_country_code"),
        SearchKey("wl{}_crypto"),
        SearchKey("wl{}_gmode_check"),
        SearchKey("wl{}_maclist_x"),
        SearchKey("wl{}_macmode"),
        SearchKey("wl{}_mbo_enable"),
        SearchKey("wl{}_mfp"),
        SearchKey("wl{}_nmode_x"),
        SearchKey("wl{}_optimizexbox_ckb"),
        SearchKey("wl{}_radio", bool_from_any),
        SearchKey("wl{}_radius_ipaddr"),
        SearchKey("wl{}_radius_key"),
        SearchKey("wl{}_radius_port"),
        SearchKey("wl{}_ssid"),
        SearchKey("wl{}_wpa_gtk_rekey"),
        SearchKey("wl{}_wpa_psk"),
    ],
    GWLAN: [
        SearchKey("wl{}_akm"),
        SearchKey("wl{}_ap_isolate"),
        SearchKey("wl{}_auth"),
        SearchKey("wl{}_auth_mode"),
        SearchKey("wl{}_auth_mode_x"),
        SearchKey("wl{}_bridge"),
        SearchKey("wl{}_bss_enabled", bool_from_any),
        SearchKey("wl{}_bss_maxassoc", int_from_str),
        SearchKey("wl{}_bw_dl", int_from_str),  # Bandwidth limit download
        SearchKey("wl{}_bw_enabled", bool_from_any),  # Bandwidth limit switch
        SearchKey("wl{}_bw_ul", int_from_str),  # Bandwidth limit upload
        SearchKey("wl{}_closed", bool_from_any),
        SearchKey("wl{}_crypto"),
        SearchKey("wl{}_expire", int_from_str),  # Expire time in s
        SearchKey("wl{}_expire_tmp", int_from_str),  # Expire time left in s
        SearchKey("wl{}_gn_wbl_enable"),
        SearchKey("wl{}_gn_wbl_rule"),
        SearchKey("wl{}_gn_wbl_type"),
        SearchKey("wl{}_hwaddr"),  # MAC address
        SearchKey("wl{}_ifname"),  # Interface name
        SearchKey("wl{}_infra"),
        SearchKey("wl{}_key"),
        SearchKey("wl{}_key1"),
        SearchKey("wl{}_key2"),
        SearchKey("wl{}_key3"),
        SearchKey("wl{}_key4"),
        SearchKey("wl{}_lanaccess", bool_from_any),  # LAN access
        SearchKey("wl{}_maclist"),
        SearchKey("wl{}_macmode"),
        SearchKey("wl{}_maxassoc", int_from_str),
        SearchKey("wl{}_mbss"),
        SearchKey("wl{}_mfp"),
        SearchKey("wl{}_mode"),
        SearchKey("wl{}_net_reauth", int_from_str),
        SearchKey("wl{}_preauth"),
        SearchKey("wl{}_radio", bool_from_any),
        SearchKey("wl{}_radius_ipaddr"),
        SearchKey("wl{}_radius_key"),
        SearchKey("wl{}_radius_port", int_from_str),
        SearchKey("wl{}_sae_anti_clog_threshold"),
        SearchKey("wl{}_sae_groups"),
        SearchKey("wl{}_sae_sync"),
        SearchKey("wl{}_ssid"),  # SSID
        SearchKey("wl{}_sta_retry_time"),
        SearchKey("wl{}_sync_node", bool_from_any),  # Sync AiMesh nodes
        SearchKey("wl{}_unit"),  # GWLAN unit id
        SearchKey("wl{}_wep", bool_from_any),
        SearchKey("wl{}_wep_x", bool_from_any),
        SearchKey("wl{}_wfi_enable", bool_from_any),
        SearchKey("wl{}_wfi_pinmode"),
        SearchKey("wl{}_wme"),
        SearchKey("wl{}_wme_bss_disable", bool_from_any),
        SearchKey("wl{}_wpa_gtk_rekey"),
        SearchKey("wl{}_wpa_psk"),  # Password
        SearchKey("wl{}_wps_mode"),
    ],
}
MAP_OVPN_CLIENT = (
    Key("REMOTE", "remote", method=ovpn_remote_fom_str),
    Key("Updated", "datetime", method=datetime_from_str),
    Key("TUN/TAP read bytes", "tun_tap_read", method=int_from_str),
    Key("TUN/TAP write bytes", "tun_tap_write", method=int_from_str),
    Key("TCP/UDP read bytes", "tcp_udp_read", method=int_from_str),
    Key("TCP/UDP write bytes", "tcp_udp_write", method=int_from_str),
    Key("Auth read bytes", "auth_read", method=int_from_str),
    Key("pre-compress bytes", "pre_compress", method=int_from_str),
    Key("post-compress bytes", "post_compress", method=int_from_str),
    Key("pre-decompress bytes", "pre_decompress", method=int_from_str),
    Key("post-decompress bytes", "post_decompress", method=int_from_str),
)
MAP_OVPN_STATUS = {
    -1: "error",
    0: "disconnected",
    1: "connecting",
    2: "connected",
}
MAP_OVPN_SERVER = (
    Key("CLIENT_LIST", "client_list"),
    Key("ROUTING_TABLE", "routing_table"),
)
MAP_PARENTAL_CONTROL_ITEM: tuple[Key, ...] = (
    Key(KEY_PARENTAL_CONTROL_MAC, MAC),
    Key(KEY_PARENTAL_CONTROL_NAME, NAME),
    Key(KEY_PARENTAL_CONTROL_TIMEMAP, TIMEMAP),
    Key(KEY_PARENTAL_CONTROL_TYPE, TYPE, int_from_str),
)
MAP_PARENTAL_CONTROL_TYPE = {
    0: DISABLE,
    1: TIME,
    2: BLOCK,
}
MAP_PORTS: tuple[Key, ...] = ()
MAP_RAM: tuple[Key, ...] = (Key(FREE), Key(TOTAL), Key(USED))
MAP_WAN = (
    Key("wanstate", STATE),
    Key("wansbstate", "bstate"),
    Key("wanauxstate", "aux"),
    Key("autodet_state"),
    Key("autodet_auxstate"),
    Key("wanlink_status", STATUS, method=bool_from_any),
    Key("wanlink_type", "ip_type"),
    Key("wanlink_ipaddr", IP),
    Key("wanlink_netmask", "mask"),
    Key("wanlink_gateway", "gateway"),
    Key("wanlink_dns", "dns"),
    Key("wanlink_lease", "lease"),
    Key("wanlink_expires", "expires"),
    Key("is_private_subnet", "private_subnet", method=int_from_str),
    Key("wanlink_xtype", "xtype"),
    Key("wanlink_xipaddr", "xip"),
    Key("wanlink_xnetmask", "xmask"),
    Key("wanlink_xgateway", "xgateway"),
    Key("wanlink_xdns", "xdns"),
    Key("wanlink_xlease", "xlease"),
    Key("wanlink_xexpires", "xexpires"),
)
RANGE_CPU_CORES = range(1, 9)  # 8 cores from 1 to 8
RANGE_GWLAN = range(1, 4)  # 3 guest WLANs from 1 to 3 per each WLAN
RANGE_OVPN_CLIENTS = range(1, 6)  # 5 Open VPN clients from 1 to 5
RANGE_OVPN_SERVERS = range(1, 3)  # 2 Open VPN servers from 1 to 2
RANGE_WLAN = range(0, 4)  # 4 WLANs from 0 to 3

### TYPES

PORT_TYPES = {
    "L": LAN,
    "U": USB,
    "W": WAN,
}

SPEED_TYPES = {
    "X": 0,
    "M": 100,
    "G": 1000,
    "Q": 2500,
}

TRAFFIC_TYPE: tuple[str, ...] = (
    RX,
    TX,
)

WLAN_TYPE: dict[str, str] = {
    WLAN_2GHZ: 0,
    WLAN_5GHZ: 1,
    WLAN_5GHZ2: 2,
    WLAN_6GHZ: 3,
}

### CONVERTERS

CONVERTERS = {
    PORT_STATUS: [
        Key("is_on", STATE, method=bool_from_any),
        Key("max_rate", method=int_from_str),
        Key(LINK_RATE, method=int_from_str),
    ]
}

### CONSTANTS, DATA TYPES AND COMMON PARAMETERS
CONST_BITSINBYTE = 8
CONST_PERCENTS = 100
CONST_ZERO = 0.0


# CHECK LEGACY FROM HERE -->

DATA_FREE = "free"
DATA_TOTAL = "total"
DATA_USAGE = "usage"
DATA_USED = "used"
DATA_RX = "rx"
DATA_TX = "tx"
DATA_TRAFFIC = [DATA_RX, DATA_TX]
DATA_BY_CORE = "core_{}"
DATA_ADD_SPEED = "{}_speed"

DEFAULT_CACHE_TIME = 5
DEFAULT_PORT = {
    "http": 80,
    "https": 8443,
}
DEFAULT_SLEEP_RECONNECT = 5
DEFAULT_SLEEP_CONNECTING = 1
DEFAULT_SLEEP_TIME = 0.1
DEFAULT_TRAFFIC_OVERFLOW = 4294967296
DEFAULT_USAGE_DIGITS = 2

PARAM_COLOR = "color"
PARAM_COUNT = "count"
PARAM_ERRNO = "errno"
PARAM_IP = "ip"
PARAM_MODE = "mode"
PARAM_RIP = "rip"
PARAM_STATE = "state"
PARAM_STATUS = "status"
PARAM_UNKNOWN = "unknown"

# OUR REGEX
REGEX_VARIABLES = r'([a-zA-Z0-9\_-]+)\s*=\s*"(.*?)"(?=;)'

# VALUES TO IGNORE
VALUES_TO_IGNORE = [str(), "None", "0.0.0.0"]

# Services to recover LED state
TRACK_SERVICES_LED = [
    "restart_wireless",
]


### ASUSWRT KEYS, MAPS AND VALUES
AR_DEFAULT_LEDG = 8

AR_KEY_AURARGB = "aurargb"
AR_KEY_HEADER = "HEADER"
AR_KEY_LED = "led_val"
AR_KEY_LEDG_COUNT = "ledg_count"
AR_KEY_LEDG_SCHEME = "ledg_scheme"
AR_KEY_LEDG_SCHEME_OLD = "ledg_scheme_old"
AR_KEY_LEDG_RGB = "ledg_rgb{}"
AR_KEY_SERVICE_COMMAND = "rc_service"
AR_KEY_SERVICE_MODIFY = "modify"
AR_KEY_SERVICE_REPLY = "run_service"

AR_LEDG_MODE: dict[int, str] = {
    1: "Gradient",
    2: "Static",
    3: "Breathing",
    4: "Evolution",
    5: "Rainbow",
    6: "Wave",
    7: "Marquee",
}

AR_MAP_RGB: dict[int, str] = {
    0: "r",
    1: "g",
    2: "b",
}
AR_MAP_SYSINFO: dict[str, list[Key]] = {
    "conn_stats_arr": [
        Key(0, "conn_total", method=int_from_str),
        Key(1, "conn_active", method=int_from_str),
    ],
    "cpu_stats_arr": [
        Key(0, "load_avg_1", method=float_from_str),
        Key(1, "load_avg_5", method=float_from_str),
        Key(2, "load_avg_15", method=float_from_str),
    ],
    "mem_stats_arr": [
        Key(0, "ram_total", method=float_from_str),
        Key(1, "ram_free", method=float_from_str),
        Key(2, "buffers", method=float_from_str),
        Key(3, "cache", method=float_from_str),
        Key(4, "swap_size", method=float_from_str),
        Key(5, "swap_total", method=float_from_str),
        Key(6, "nvram_used", method=int_from_str),
        Key(7, "jffs"),
    ],
    "wlc_24_arr": [
        Key(0, "2ghz_clients_associated", method=bool_or_int),
        Key(1, "2ghz_clients_authorized", method=bool_or_int),
        Key(2, "2ghz_clients_authenticated", method=bool_or_int),
    ],
    "wlc_51_arr": [
        Key(0, "5ghz_clients_associated", method=bool_or_int),
        Key(1, "5ghz_clients_authorized", method=bool_or_int),
        Key(2, "5ghz_clients_authenticated", method=bool_or_int),
    ],
    "wlc_52_arr": [
        Key(0, "5ghz2_clients_associated", method=bool_or_int),
        Key(1, "5ghz2_clients_authorized", method=bool_or_int),
        Key(2, "5ghz2_clients_authenticated", method=bool_or_int),
    ],
}
AR_MAP_TEMPERATURE: dict[str, list[str]] = {
    "2ghz": [
        'curr_coreTmp_2_raw="([0-9.]+)&deg;C',
        'curr_coreTmp_0_raw="([0-9.]+)&deg;C',
        'curr_coreTmp_wl0_raw="([0-9.]+)&deg;C',
    ],
    "5ghz": [
        'curr_coreTmp_5_raw="([0-9.]+)&deg;C',
        'curr_coreTmp_1_raw="([0-9.]+)&deg;C',
        'curr_coreTmp_wl1_raw="([0-9.]+)&deg;C',
    ],
    "5ghz2": [
        'curr_coreTmp_52_raw="([0-9.]+)&deg;C',
        'curr_coreTmp_2_raw="([0-9.]+)&deg;C',
        'curr_coreTmp_wl2_raw="([0-9.]+)&deg;C',
    ],
    "6ghz": [
        'curr_coreTmp_3_raw="([0-9.]+)&deg;C',
        'curr_coreTmp_wl3_raw="([0-9.]+)&deg;C',
    ],
    "cpu": ['curr_cpuTemp="([0-9.]+)"', 'curr_coreTmp_cpu="([0-9.]+)"'],
}

### ASUSWRT SERVICES

AR_FIRMWARE_CHECK_COMMAND = "firmware_check"
AR_SERVICE_COMMAND: dict[str, str] = {
    "force_restart": "restart_{}_force",
    "start": "start_{}",
    "stop": "stop_{}",
    "restart": "restart_{}",
}
AR_SERVICE_CONTROL: dict[str, list[str]] = {
    "firewall": [
        "restart",
    ],
    "ftpd": [
        "force_restart",
        "start",
        "stop",
        "restart",
    ],
    "httpd": [
        "restart",
    ],
    "wireless": [
        "restart",
    ],
}
AR_SERVICE_DROP_CONNECTION: list[str] = {
    "httpd",
}

### ERRORS AND MESSAGES
ERROR_IDENTITY = "Cannot obtain identity from the device {}. Exception summary{}"
ERROR_PARSING = (
    "Failed parsing value '{}'. Please report this issue. Exception summary: {}"
)
ERROR_SERVICE = (
    "Error calling service '{}'. "
    "Service did not return any expected value in the reply: {}"
)
ERROR_SERVICE_UNKNOWN = "Unknown service '{}' with mode '{}'"
ERROR_VALUE = "Wrong value '{}' with original exception: {}"
ERROR_VALUE_TYPE = "Wrong value '{}' of type {}"
ERROR_ZERO_DIVISION = "Zero division allert: {}"

INTERFACE_TYPE = {
    "wan_ifnames": "wan",
    "wl_ifnames": "wlan",
    "wl0_vifnames": "gwlan2",
    "wl1_vifnames": "gwlan5",
    "lan_ifnames": "lan",
}

NVRAM_LIST = {
    "DEVICE": [
        "productid",
        "serial_no",
        "label_mac",
        "model",
        "pci/1/1/ATE_Brand",
    ],
    "MODE": [
        "sw_mode",
        "wlc_psta",
        "wlc_express",
    ],
    "FIRMWARE": [
        "firmver",
        "buildno",
        "extendno",
    ],
    "FUNCTIONS": [
        "rc_support",
        "ss_support",
    ],
    "INTERFACES": [
        "wans_dualwan",
        "wan_ifnames",
        "wl_ifnames",
        "wl0_vifnames",
        "wl1_vifnames",
        "lan_ifnames",
        "br0_ifnames",
    ],
    "REBOOT": [
        "reboot_schedule",
        "reboot_schedule_enable",
        "reboot_time",
    ],
    "WAN0": [
        "link_wan",
        "wan0_auxstate_t",
        "wan0_dns",
        "wan0_enable",
        "wan0_expires",
        "wan0_gateway",
        "wan0_gw_ifname",
        "wan0_gw_mac",
        "wan0_hwaddr",
        "wan0_ipaddr",
        "wan0_is_usb_modem_ready",
        "wan0_primary",
        "wan0_proto",
        "wan0_realip_ip",
        "wan0_realip_state",
        "wan0_sbstate_t",
        "wan0_state_t",
        "wan0_upnp_enable",
    ],
    "WAN1": [
        "link_wan1",
        "wan1_auxstate_t",
        "wan1_dns",
        "wan1_enable",
        "wan1_gateway",
        "wan1_gw_ifname",
        "wan1_gw_mac",
        "wan1_hwaddr",
        "wan1_ipaddr",
        "wan1_is_usb_modem_ready",
        "wan1_primary",
        "wan1_proto",
        "wan1_realip_ip",
        "wan1_realip_state",
        "wan1_sbstate_t",
        "wan1_state_t",
        "wan1_upnp_enable",
    ],
    "LAN": [
        "lan_gateway",
        "lan_hwaddr",
        "lan_ifname",
        "lan_ifnames",
        "lan_ipaddr",
        "lan_netmask",
        "lan_proto",
        "lanports",
    ],
    "WLAN0": [
        "wl0_radio",
        "wl0_ssid",
        "wl0_chanspec",
        "wl0_closed",
        "wl0_nmode_x",
        "wl0_bw",
        "wl0_auth_mode_x",
        "wl0_crypto",
        "wl0_wpa_psk",
        "wl0_mfp",
        "wl0_mbo_enable",
        "wl0_country_code",
        "wl0_maclist_x",
        "wl0_macmode",
    ],
    "WLAN1": [
        "wl1_radio",
        "wl1_ssid",
        "wl1_chanspec",
        "wl1_closed",
        "wl1_nmode_x",
        "wl1_bw",
        "wl1_auth_mode_x",
        "wl1_crypto",
        "wl1_wpa_psk",
        "wl1_mfp",
        "wl1_mbo_enable",
        "wl1_country_code",
        "wl1_maclist_x",
        "wl1_macmode",
    ],
    "GWLAN01": [
        "wl0.1_bss_enabled",
        "wl0.1_ssid",
        "wl0.1_auth_mode_x",
        "wl0.1_crypto",
        "wl0.1_key",
        "wl0.1_wpa_psk",
        "wl0.1_lanaccess",
        "wl0.1_expire",
        "wl0.1_expire_tmp",
        "wl0.1_macmode",
        "wl0.1_mbss",
        "wl0.1_sync_mode",
    ],
    "GWLAN02": [
        "wl0.2_bss_enabled",
        "wl0.2_ssid",
        "wl0.2_auth_mode_x",
        "wl0.2_crypto",
        "wl0.2_key",
        "wl0.2_wpa_psk",
        "wl0.2_lanaccess",
        "wl0.2_expire",
        "wl0.2_expire_tmp",
        "wl0.2_macmode",
        "wl0.2_mbss",
        "wl0.2_sync_mode",
    ],
    "GWLAN03": [
        "wl0.3_bss_enabled",
        "wl0.3_ssid",
        "wl0.3_auth_mode_x",
        "wl0.3_crypto",
        "wl0.3_key",
        "wl0.3_wpa_psk",
        "wl0.3_lanaccess",
        "wl0.3_expire",
        "wl0.3_expire_tmp",
        "wl0.3_macmode",
        "wl0.3_mbss",
        "wl0.3_sync_mode",
    ],
    "GWLAN11": [
        "wl1.1_bss_enabled",
        "wl1.1_ssid",
        "wl1.1_auth_mode_x",
        "wl1.1_crypto",
        "wl1.1_key",
        "wl1.1_wpa_psk",
        "wl1.1_lanaccess",
        "wl1.1_expire",
        "wl1.1_expire_tmp",
        "wl1.1_macmode",
        "wl1.1_mbss",
        "wl1.1_sync_mode",
    ],
    "GWLAN12": [
        "wl1.2_bss_enabled",
        "wl1.2_ssid",
        "wl1.2_auth_mode_x",
        "wl1.2_crypto",
        "wl1.2_key",
        "wl1.2_wpa_psk",
        "wl1.2_lanaccess",
        "wl1.2_expire",
        "wl1.2_expire_tmp",
        "wl1.2_macmode",
        "wl1.2_mbss",
        "wl1.2_sync_mode",
    ],
    "GWLAN13": [
        "wl1.3_bss_enabled",
        "wl1.3_ssid",
        "wl1.3_auth_mode_x",
        "wl1.3_crypto",
        "wl1.3_key",
        "wl1.3_wpa_psk",
        "wl1.3_lanaccess",
        "wl1.3_expire",
        "wl1.3_expire_tmp",
        "wl1.3_macmode",
        "wl1.3_mbss",
        "wl1.3_sync_mode",
    ],
}

KEY_NVRAM_GET = "nvram_get"
KEY_ACTION_MODE = "action_mode"
KEY_HOOK = "hook"
DEFAULT_ACTION_MODE = "apply"


### DEVICEMAP

# These values are just stored directly in this order in the corresponding node
DEVICEMAP_BY_INDEX = {
    WAN: {
        "wan": [
            "status",
            "sbstatus",
            "auxstatus",
        ],
    },
    f"{WAN}0": {
        "first_wan": [
            "status",
            "sbstatus",
            "auxstatus",
        ],
    },
    f"{WAN}1": {
        "second_wan": [
            "status",
            "sbstatus",
            "auxstatus",
        ],
    },
    USB: {
        "usb": [
            "status",
        ],
    },
}


# Not implemented yet
# psta:wlc_state=0;wlc_state_auth=0;
DEVICEMAP_SPECIAL = {
    WAN: {
        "psta": [
            "wlc_state",
            "wlc_state_auth",
        ],
    },
}

# These values are stored as "key=value"
DEVICEMAP_GENERAL = {
    WAN: {
        "wan": [
            "monoClient",
            "wlc_state",
            "wlc_sbstate",
            "wifi_hw_switch",
            "ddnsRet",
            "ddnsUpdate",
            "wan_line_state",
            "wlan0_radio_flag",
            "wlan1_radio_flag",
            "wlan2_radio_flag",
            "data_rate_info_2g",
            "data_rate_info_5g",
            "data_rate_info_5g_2",
            "wan_diag_state",
            "active_wan_unit",
            "wlc0_state",
            "wlc1_state",
            "rssi_2g",
            "rssi_5g",
            "rssi_5g_2",
            "link_internet",
            "wlc2_state",
            "le_restart_httpd",
        ],
    },
    VPN: {
        "vpn": [
            "vpnc_proto",
            "vpnc_state_t",
            "vpnc_sbstate_t",
            "vpn_client1_state",
            "vpn_client2_state",
            "vpn_client3_state",
            "vpn_client4_state",
            "vpn_client5_state",
            "vpnd_state",
            "vpn_client1_errno",
            "vpn_client2_errno",
            "vpn_client3_errno",
            "vpn_client4_errno",
            "vpn_client5_errno",
        ],
    },
    SYS: {
        "sys": [
            "uptimeStr",
        ],
    },
    QTN: {
        "qtn": [
            "qtn_state",
        ],
    },
    USB: {
        "usb": [
            "modem_enable",
        ],
    },
    f"{WAN}0": {
        "wan": [
            "wan0_enable",
            "wan0_realip_state",
            "wan0_ipaddr",
            "wan0_realip_ip",
        ],
    },
    f"{WAN}1": {
        "wan": [
            "wan1_enable",
            "wan1_realip_state",
            "wan1_ipaddr",
            "wan1_realip_ip",
        ],
    },
    SIM: {
        "sim": [
            "sim_state",
            "sim_signal",
            "sim_operation",
            "sim_isp",
            "roaming",
            "roaming_imsi",
            "sim_imsi",
            "g3err_pin",
            "pin_remaining_count",
            "modem_act_provider",
            "rx_bytes",
            "tx_bytes",
            "modem_sim_order",
        ],
    },
    DHCP: {
        "dhcp": [
            "dnsqmode",
        ],
    },
    DIAG: {
        "diag": [
            "diag_dblog_enable",
            "diag_dblog_remaining",
        ]
    },
}

# This should be cleared from the data
DEVICEMAP_CLEAR = {
    WAN: {
        "data_rate_info_2g": '"',
        "data_rate_info_5g": '"',
        "data_rate_info_5g_2": '"',
    }
}
