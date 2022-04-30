"""AsusRouter constants module"""

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

DEFAULT_SLEEP_RECONNECT = 5
DEFAULT_SLEEP_CONNECTING = 1
DEFAULT_SLEEP_TIME = 0.1

DEFAULT_PORT = {
    "http": 80,
    "https": 8443,
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

MSG_ERROR = {
    "authorisation": "Session is not authorised",
    "cert_missing": "CA certificate is missing",
    "command": "Error sending a command",
    "credentials": "Wrong credentials",
    "disabled_control": "Device is connected in no-control mode. Sending commands is blocked",
    "disabled_monitor": "Device is connected in no-monitor mode. Sending hooks is blocked",
    "token": "Cannot recieve a token from device",
    "try_again": "Too many attempts",
    "unknown": "Unknown error",
}

MSG_WARNING = {
    "not_connected": "Not connected",
    "refused": "Connection refused",
}

MSG_INFO = {
    "json_fix": "Trying to fix JSON response",
    "reconnect": "Reconnecting",
    "no_cert": "No certificate provided. Using trusted",
    "no_cert_check": "Certificate won't be checked",
    "xml": "Data is in XML",
}

MSG_SUCCESS = {
    "cert_found": "CA certificate found",
    "command": "Command was sent successfully",
    "hook": "Hook was sent successfully",
    "load": "Page was loaded successfully",
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
    "netdev" : "appobj"
}

TRAFFIC_GROUPS = {
    "INTERNET" : "WAN",    # main WAN
    "INTERNET1" : "USB",   # secondary WAN (USB modem / phone)
    "WIRED" : "WIRED",      # wired connections
    "BRIDGE" : "BRIDGE",    # bridge
    "WIRELESS0" : "WLAN0",  # 2.4 GHz WiFi
    "WIRELESS1" : "WLAN1",  # 5 GHz WiFi
    "WIRELESS2" : "WLAN2",  # 5 GHz WiFi #2 (<-- check)
}

NETWORK_DATA = [
    "rx",
    "tx",
]

PORT_TYPE = [
    "LAN",
    "WAN",
]

KEY_NVRAM_GET = "nvram_get"


