"""Constants for the devicemap endpoint module."""

# These values are just stored directly in this order in the corresponding node
# Format: (output_group, input_group, [input_values])
DEVICEMAP_BY_INDEX = [
    ("wan", "wan", ["status", "sbstatus", "auxstatus"]),
    ("wan0", "first_wan", ["status", "sbstatus", "auxstatus"]),
    ("wan1", "second_wan", ["status", "sbstatus", "auxstatus"]),
    ("usb", "usb", ["status"]),
]

# These values are stored as "key=value"
# Format: (output_group, input_group, [input_values])
DEVICEMAP_BY_KEY = [
    (
        "wan",
        "wan",
        [
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
    ),
    (
        "vpn",
        "vpn",
        [
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
            "vpn_server1_state",
            "vpn_server2_state",
        ],
    ),
    (
        "sys",
        "sys",
        [
            "uptimeStr",
        ],
    ),
    (
        "qtn",
        "qtn",
        [
            "qtn_state",
        ],
    ),
    (
        "usb",
        "usb",
        [
            "modem_enable",
        ],
    ),
    (
        "wan0",
        "wan",
        [
            "wan0_enable",
            "wan0_realip_state",
            "wan0_ipaddr",
            "wan0_realip_ip",
        ],
    ),
    (
        "wan1",
        "wan",
        [
            "wan1_enable",
            "wan1_realip_state",
            "wan1_ipaddr",
            "wan1_realip_ip",
        ],
    ),
    (
        "sim",
        "sim",
        [
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
    ),
    (
        "dhcp",
        "dhcp",
        [
            "dnsqmode",
        ],
    ),
    (
        "diag",
        "diag",
        [
            "diag_dblog_enable",
            "diag_dblog_remaining",
        ],
    ),
]

# This data should be cleared from some symbols
# Format: {output_group: {key: value_to_remove}}
DEVICEMAP_CLEAR = {
    "wan": {
        "data_rate_info_2g": '"',
        "data_rate_info_5g": '"',
        "data_rate_info_5g_2": '"',
    }
}

# This data is stored in a special way
# psta:wlc_state=0;wlc_state_auth=0;
# as a single value
# We need to split it into multiple values and store them in the corresponding group
# Format: (output_group, input_group, input_subgroup, [input_values])
# This part is not used in the current version of the library
DEVICEMAP_SPECIAL = [
    ("wan", "wan", "psta", ["wlc_state", "wlc_state_auth"]),
]
