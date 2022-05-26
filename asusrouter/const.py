"""AsusRouter constants module"""

from asusrouter.dataclass import Key
from asusrouter.util.converters import bool_from_any, exists_or_not, int_from_str, float_from_str, time_from_delta, service_support

#Use the last known working Android app user-agent, so the device will reply
#AR_USER_AGENT = "asusrouter-Android-DUTUtil-1.0.0.255"
#Or use just "asusrouter--DUTUtil-", since only this is needed for a correct replies
AR_USER_AGENT = "asusrouter--DUTUtil-"
#Or even this - all the response will be correct, but the HTTP header will be missing 'AiHOMEAPILevel', 'Httpd_AiHome_Ver' and 'Model_Name' on connect
#AR_USER_AGENT = "asusrouter--"


AR_API = [
    "Model_Name",
    "AiHOMEAPILevel",
    "Httpd_AiHome_Ver",
]

CONST_BITSINBYTE = 8
CONST_PERCENTS = 100
CONST_ZERO = 0.0

DATA_FREE = "free"
DATA_TOTAL = "total"
DATA_USAGE = "usage"
DATA_USED = "used"
DATA_RX = "rx"
DATA_TX = "tx"
DATA_TRAFFIC = [DATA_RX, DATA_TX]

DATA_BY_CORE = "core_{}"
DATA_ADD_SPEED = "{}_speed"

DEFAULT_TRAFFIC_OVERFLOW = 4294967296

KEY_CPU = "CPU"
KEY_RAM = "RAM"
KEY_NETWORK = "NETWORK"
KEY_WAN = "WAN"

AR_DEVICE_IDENTITY : tuple[Key, ...] = (
    Key("serial_no", "serial"),
    Key("label_mac", "mac"),
    Key("model", "model"),
    Key("firmver", "fw_major"),
    Key("buildno", "fw_minor"),
    Key("extendno", "fw_build"),
    Key("rc_support", "services", method = service_support),
    Key("ss_support", "services", method = service_support),
    Key("led_val", "led", method = exists_or_not)
)

AR_DEVICE_ATTRIBUTES_LIST : tuple[Key, ...] = (
    Key("mac", "name"),
    Key("name", "name"),
    Key("nickName", "name"),
    Key("mac"),
    Key("ip"),
    Key("ipMethod", "ip_method"),
    Key("internetState", "internet_state", method = bool_from_any),
    Key("internetMode", "internet_mode", method = bool_from_any),
    Key("isWL", "connection_type", method = int_from_str),
    Key("isOnline", "online", method = bool_from_any),
    Key("rssi", method = int_from_str),
    Key("wlConnectTime", "connected_since", time_from_delta),
    Key("curRx", "rx_speed", method = float_from_str),
    Key("curTx", "tx_speed", method = float_from_str),
)
AR_KEY_CPU = "cpu_usage"
AR_KEY_CPU_ITEM = "cpu{}_{}"
AR_KEY_CPU_LIST : tuple[Key, ...] = (
    Key(DATA_TOTAL),
    Key(DATA_USAGE, DATA_USED)
)
AR_KEY_DEVICE_NAME_LIST = ["nickName", "name", "mac"]
AR_KEY_DEVICEMAP = "devicemap"
AR_KEY_DEVICES = "get_clientlist"
AR_KEY_DEVICES_LIST = "maclist"
AR_KEY_LED = "led_val"
AR_KEY_NETWORK = "netdev"
AR_KEY_NETWORK_ITEM = "{}_{}"
AR_KEY_RAM = "memory_usage"
AR_KEY_RAM_ITEM = "mem_{}"
AR_KEY_RAM_LIST = [DATA_FREE, DATA_TOTAL, DATA_USED]
AR_KEY_SERVICE_COMMAND = "rc_service"
AR_KEY_SERVICE_MODIFY = "modify"
AR_KEY_SERVICE_REPLY = "run_service"


AR_KEY_NETWORK_GROUPS = {
    "INTERNET" : "WAN",     # main WAN
    "INTERNET1" : "USB",    # secondary WAN (USB modem / phone)
    "WIRED" : "WIRED",      # wired connections
    "BRIDGE" : "BRIDGE",    # bridge
    "WIRELESS0" : "WLAN0",  # 2.4 GHz WiFi
    "WIRELESS1" : "WLAN1",  # 5 GHz WiFi
    "WIRELESS2" : "WLAN2",  # 5 GHz WiFi #2 (<-- check)
}
AR_KEY_WAN = "wanlink_state"
AR_KEY_WAN_STATE = (
    Key("wanstate", "state"),
    Key("wansbstate", "bstate"),
    Key("wanauxstate", "aux",),
    Key("autodet_state"),
    Key("autodet_auxstate",),
    Key("wanlink_status", "status"),
    Key("wanlink_type", "ip_type"),
    Key("wanlink_ipaddr", "ip"),
    Key("wanlink_netmask", "mask"),
    Key("wanlink_gateway", "gateway"),
    Key("wanlink_dns", "dns"),
    Key("wanlink_lease", "lease"),
    Key("wanlink_expires", "expires"),
    Key("is_private_subnet", "private_subnet"),
    Key("wanlink_xtype", "xtype"),
    Key("wanlink_xipaddr", "xip"),
    Key("wanlink_xnetmask", "xmask"),
    Key("wanlink_xgateway", "xgateway"),
    Key("wanlink_xdns", "xdns"),
    Key("wanlink_xlease", "xlease",),
    Key("wanlink_xexpires", "xexpires"),
)

AR_HOOK_TEMPLATE = "{}({});"
AR_HOOK_DEVICES = "{}()".format(AR_KEY_DEVICES)

AR_SERVICE_CONTROL : dict[str, list[str]] = {
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

AR_SERVICE_COMMAND : dict[str, str] = {
    "force_restart": "restart_{}_force",
    "start": "start_{}",
    "stop": "stop_{}",
    "restart": "restart_{}",
}

AR_SERVICE_DROP_CONNECTION : list[str] = {
    "httpd",
}

AR_DEFAULT_CORES = [ 1 ]
AR_DEFAULT_CORES_RANGE = range(1, 8)

DEFAULT_USAGE_DIGITS = 2


DEFAULT_CACHE_TIME = 5

DEFAULT_SLEEP_RECONNECT = 5
DEFAULT_SLEEP_CONNECTING = 1
DEFAULT_SLEEP_TIME = 0.1

DEFAULT_PORT = {
    "http": 80,
    "https": 8443,
}

AR_KEY = {
    "cpu_usage": "cpu_usage",
}

AR_PATH = {
    "command": "applyapp.cgi",
    "devicemap": "ajax_status.xml",
    "get": "appGet.cgi",
    "login": "login.cgi",
    "logout": "Logout.asp",
    "ports": "ajax_ethernet_ports.asp",
}

AR_ERROR = {
    "authorisation": 2,
    "credentials": 3,
    "try_again": 7,
    "logout": 8,
}

ERROR_IDENTITY = "Cannot obtain identity from the device {}. Exception summary{}"
ERROR_PARSING = "Failed parsing value '{}'. Please report this issue. Exception summary: {}"
ERROR_SERVICE = "Error calling service '{}'. Service did not return any expected value in the reply: {}"
ERROR_SERVICE_UNKNOWN = "Unknown service '{}' with mode '{}'"
ERROR_VALUE = "Wrong value '{}' with original exception: {}"
ERROR_VALUE_TYPE = "Wrong value '{}' of type {}"
ERROR_ZERO_DIVISION = "Zero division allert: {}"

MSG_ERROR = {
    "authorisation": "Session is not authorised",
    "cert_missing": "CA certificate is missing",
    "command": "Error sending a command {} to {}",
    "credentials": "Wrong credentials",
    "disabled_control": "Device is connected in no-control mode. Sending commands is blocked",
    "disabled_monitor": "Device is connected in no-monitor mode. Sending hooks is blocked",
    "token": "Cannot recieve a token from device",
    "try_again": "Too many attempts",
    "unknown": "Unknown error code {}",
}

MSG_WARNING = {
    "not_connected": "Not connected",
    "refused": "Connection refused",
}

MSG_INFO = {
    "drop_connection_service": "Connection will be dropped on behalf of '{}' service",
    "error_flag": "Error flag found",
    "empty_reqquest": "This request is empty",
    "identifying": "Identifying the device",
    "json_fix": "Trying to fix JSON response",
    "monitor_sleep": "Monitor {} is already active -> sleep",
    "monitor_wakeup": "Monitor {} woke up -> closing",
    "no_cert": "No certificate provided. Using trusted",
    "no_cert_check": "Certificate won't be checked",
    "reconnect": "Reconnecting",
    "service": "Service '{}' was called with arguments '{}' successfully. Reply: {}",
    "xml": "Data is in XML",
}

MSG_SUCCESS = {
    "cert_found": "CA certificate found",
    "command": "Command was sent successfully",
    "hook": "Hook was sent successfully",
    "identity": "Identity collected",
    "load": "Page {} was loaded successfully",
    "login": "Login successful",
    "logout": "Logout successful",
}

INTERFACE_TYPE = {
    "wan_ifnames": "wan",
    "wl_ifnames": "wlan",
    "wl0_vifnames": "gwlan2",
    "wl1_vifnames": "gwlan5",
    "lan_ifnames": "lan"
}

NVRAM_LIST = {
    "DEVICE": ["productid", "serial_no", "label_mac", "model", "pci/1/1/ATE_Brand", ],
    "MODE": ["sw_mode", "wlc_psta", "wlc_express", ],
    "FIRMWARE": ["firmver", "buildno", "extendno", ],
    "FUNCTIONS": ["rc_support", "ss_support", ],
    "INTERFACES": ["wans_dualwan", "wan_ifnames", "wl_ifnames", "wl0_vifnames", "wl1_vifnames", "lan_ifnames", "br0_ifnames", ],
    "REBOOT": ["reboot_schedule", "reboot_schedule_enable", "reboot_time", ],
    "WAN0": ["link_wan", "wan0_auxstate_t", "wan0_dns", "wan0_enable", "wan0_expires", "wan0_gateway", "wan0_gw_ifname", "wan0_gw_mac", "wan0_hwaddr", "wan0_ipaddr", "wan0_is_usb_modem_ready", "wan0_primary", "wan0_proto", "wan0_realip_ip", "wan0_realip_state", "wan0_sbstate_t", "wan0_state_t", "wan0_upnp_enable", ],
    "WAN1": ["link_wan1", "wan1_auxstate_t", "wan1_dns", "wan1_enable", "wan1_gateway", "wan1_gw_ifname", "wan1_gw_mac", "wan1_hwaddr", "wan1_ipaddr", "wan1_is_usb_modem_ready", "wan1_primary", "wan1_proto", "wan1_realip_ip", "wan1_realip_state", "wan1_sbstate_t", "wan1_state_t", "wan1_upnp_enable", ],
    "LAN": ["lan_gateway", "lan_hwaddr", "lan_ifname", "lan_ifnames", "lan_ipaddr", "lan_netmask", "lan_proto", "lanports", ],
    "WLAN0": ["wl0_radio", "wl0_ssid", "wl0_chanspec", "wl0_closed", "wl0_nmode_x", "wl0_bw", "wl0_auth_mode_x", "wl0_crypto", "wl0_wpa_psk", "wl0_mfp", "wl0_mbo_enable", "wl0_country_code", "wl0_maclist_x", "wl0_macmode", ],
    "WLAN1": ["wl1_radio", "wl1_ssid", "wl1_chanspec", "wl1_closed", "wl1_nmode_x", "wl1_bw", "wl1_auth_mode_x", "wl1_crypto", "wl1_wpa_psk", "wl1_mfp", "wl1_mbo_enable", "wl1_country_code", "wl1_maclist_x", "wl1_macmode", ],
    "GWLAN01": ["wl0.1_bss_enabled", "wl0.1_ssid", "wl0.1_auth_mode_x", "wl0.1_crypto", "wl0.1_key", "wl0.1_wpa_psk", "wl0.1_lanaccess", "wl0.1_expire", "wl0.1_expire_tmp", "wl0.1_macmode", "wl0.1_mbss", "wl0.1_sync_mode", ],
    "GWLAN02": ["wl0.2_bss_enabled", "wl0.2_ssid", "wl0.2_auth_mode_x", "wl0.2_crypto", "wl0.2_key", "wl0.2_wpa_psk", "wl0.2_lanaccess", "wl0.2_expire", "wl0.2_expire_tmp", "wl0.2_macmode", "wl0.2_mbss", "wl0.2_sync_mode", ],
    "GWLAN03": ["wl0.3_bss_enabled", "wl0.3_ssid", "wl0.3_auth_mode_x", "wl0.3_crypto", "wl0.3_key", "wl0.3_wpa_psk", "wl0.3_lanaccess", "wl0.3_expire", "wl0.3_expire_tmp", "wl0.3_macmode", "wl0.3_mbss", "wl0.3_sync_mode", ],
    "GWLAN11": ["wl1.1_bss_enabled", "wl1.1_ssid", "wl1.1_auth_mode_x", "wl1.1_crypto", "wl1.1_key", "wl1.1_wpa_psk", "wl1.1_lanaccess", "wl1.1_expire", "wl1.1_expire_tmp", "wl1.1_macmode", "wl1.1_mbss", "wl1.1_sync_mode", ],
    "GWLAN12": ["wl1.2_bss_enabled", "wl1.2_ssid", "wl1.2_auth_mode_x", "wl1.2_crypto", "wl1.2_key", "wl1.2_wpa_psk", "wl1.2_lanaccess", "wl1.2_expire", "wl1.2_expire_tmp", "wl1.2_macmode", "wl1.2_mbss", "wl1.2_sync_mode", ],
    "GWLAN13": ["wl1.3_bss_enabled", "wl1.3_ssid", "wl1.3_auth_mode_x", "wl1.3_crypto", "wl1.3_key", "wl1.3_wpa_psk", "wl1.3_lanaccess", "wl1.3_expire", "wl1.3_expire_tmp", "wl1.3_macmode", "wl1.3_mbss", "wl1.3_sync_mode", ],
}

MONITOR_MAIN = {
    "cpu_usage" : "appobj",
    "memory_usage" : "appobj",
    "netdev" : "appobj",
    "wanlink_state" : "appobj",
}

PORT_TYPE = [
    "LAN",
    "WAN",
]

KEY_NVRAM_GET = "nvram_get"
KEY_ACTION_MODE = "action_mode"
KEY_HOOK = "hook"
DEFAULT_ACTION_MODE = "apply"


### DEVICEMAP

# These values are just stored directly in this order in the corresponding node
DEVICEMAP_BY_INDEX = {
    "WAN": { "wan": ["status", "sbstatus", "auxstatus", ], },
    "WAN0": { "first_wan": ["status", "sbstatus", "auxstatus", ], },
    "WAN1": { "second_wan": [ "status", "sbstatus", "auxstatus", ], },
    "USB": { "usb": [ "status", ], },
}


#Not implemented yet
#psta:wlc_state=0;wlc_state_auth=0;
DEVICEMAP_SPECIAL = {
    "WAN": {
        "psta": [
            "wlc_state",
            "wlc_state_auth",
        ],
    },
}

# These values are stored as "key=value"
DEVICEMAP_GENERAL = {
    "WAN": {
        "wan": [ "monoClient", "wlc_state", "wlc_sbstate", "wifi_hw_switch", "ddnsRet", "ddnsUpdate", "wan_line_state", "wlan0_radio_flag", "wlan1_radio_flag", "wlan2_radio_flag", "data_rate_info_2g", "data_rate_info_5g", "data_rate_info_5g_2", "wan_diag_state", "active_wan_unit", "wlc0_state", "wlc1_state", "rssi_2g", "rssi_5g", "rssi_5g_2", "link_internet", "wlc2_state", "le_restart_httpd", ],
    },
    "VPN": {
        "vpn": [ "vpnc_proto", "vpnc_state_t", "vpnc_sbstate_t", "vpn_client1_state", "vpn_client2_state", "vpn_client3_state", "vpn_client4_state", "vpn_client5_state", "vpnd_state", "vpn_client1_errno", "vpn_client2_errno", "vpn_client3_errno", "vpn_client4_errno", "vpn_client5_errno", ],
    },
    "SYS": {
        "sys": [ "uptimeStr", ],
    },
    "QTN": {
        "qtn": [ "qtn_state", ],
    },
    "USB": {
        "usb": [ "modem_enable", ],
    },
    "WAN0": {
        "wan": [ "wan0_enable", "wan0_realip_state", "wan0_ipaddr", "wan0_realip_ip", ],
    },
    "WAN1": {
        "wan": [ "wan1_enable", "wan1_realip_state", "wan1_ipaddr", "wan1_realip_ip", ],
    },
    "SIM": {
        "sim": [ "sim_state", "sim_signal", "sim_operation", "sim_isp", "roaming", "roaming_imsi", "sim_imsi", "g3err_pin", "pin_remaining_count", "modem_act_provider", "rx_bytes", "tx_bytes", "modem_sim_order", ],
    },
    "DHCP": {
        "dhcp": [ "dnsqmode", ],
    },
    "DIAG": {
        "diag": [ "diag_dblog_enable", "diag_dblog_remaining", ]
    }
}

# This should be cleared from the data
DEVICEMAP_CLEAR = {
    "WAN": {
        "data_rate_info_2g": "\"",
        "data_rate_info_5g": "\"",
        "data_rate_info_5g_2": "\"",
    }
}


