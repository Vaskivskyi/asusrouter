"""Result of processing devicemap_001.content."""

from datetime import datetime

from dateutil.tz import tzoffset

from asusrouter import AsusData
from asusrouter.modules.openvpn import AsusOVPNClient, AsusOVPNServer

expected_result = {
    AsusData.DEVICEMAP: {
        "wan": {
            "status": "2",
            "sbstatus": "0",
            "auxstatus": "0",
            "monoClient": None,
            "wlc_state": "0",
            "wlc_sbstate": "0",
            "wifi_hw_switch": "1",
            "ddnsRet": None,
            "ddnsUpdate": None,
            "line_state": None,
            "wlan0_radio_flag": "1",
            "wlan1_radio_flag": "1",
            "wlan2_radio_flag": None,
            "data_rate_info_2g": "72 Mbps",
            "data_rate_info_5g": "1921.5 Mbps",
            "data_rate_info_5g_2": "0 Mbps",
            "diag_state": None,
            "active_wan_unit": "0",
            "wlc0_state": None,
            "wlc1_state": None,
            "rssi_2g": None,
            "rssi_5g": None,
            "rssi_5g_2": None,
            "link_internet": "2",
            "wlc2_state": None,
            "le_restart_httpd": None,
        },
        "wan0": {
            "status": "2",
            "sbstatus": "0",
            "auxstatus": "0",
            "enable": "1",
            "realip_state": "2",
            "ipaddr": "111.222.111.222",
            "realip_ip": "111.222.111.222",
        },
        "wan1": {
            "status": "0",
            "sbstatus": "0",
            "auxstatus": "0",
            "enable": "1",
            "realip_state": "0",
            "ipaddr": "0.0.0.0",
            "realip_ip": None,
        },
        "usb": {"status": "'[]'", "modem_enable": "1"},
        "vpn": {
            "vpnc_proto": "disable",
            "vpnc_state_t": "0",
            "vpnc_sbstate_t": "0",
            "client1_state": "0",
            "client2_state": None,
            "client3_state": "0",
            "client4_state": "-1",
            "client5_state": None,
            "vpnd_state": "0",
            "client1_errno": "0",
            "client2_errno": None,
            "client3_errno": "0",
            "client4_errno": "8",
            "client5_errno": None,
            "server1_state": "2",
            "server2_state": None,
        },
        "sys": {
            "uptimeStr": "Sun, 19 Nov 2023 15:51:06 +0100(509356 secs "
            "since boot)"
        },
        "qtn": {"state": None},
        "sim": {
            "state": None,
            "signal": None,
            "operation": None,
            "isp": None,
            "roaming": "0",
            "roaming_imsi": None,
            "imsi": None,
            "g3err_pin": None,
            "pin_remaining_count": None,
            "modem_act_provider": None,
            "rx_bytes": None,
            "tx_bytes": None,
            "modem_sim_order": None,
        },
        "dhcp": {"dnsqmode": None},
        "diag": {"dblog_enable": "0", "dblog_remaining": "0"},
    },
    AsusData.BOOTTIME: {
        "datetime": datetime(
            2023, 11, 13, 18, 21, 50, tzinfo=tzoffset(None, 3600)
        ),
        "uptime": 509356,
    },
    AsusData.OPENVPN: {
        "client": {
            1: {"state": AsusOVPNClient.DISCONNECTED, "errno": 0},
            2: {"state": AsusOVPNClient.DISCONNECTED, "errno": None},
            3: {"state": AsusOVPNClient.DISCONNECTED, "errno": 0},
            4: {"state": AsusOVPNClient.ERROR, "errno": 8},
            5: {"state": AsusOVPNClient.DISCONNECTED, "errno": None},
        },
        "server": {
            1: {"state": AsusOVPNServer.CONNECTED},
            2: {"state": AsusOVPNServer.DISCONNECTED},
        },
    },
    AsusData.FLAGS: {},
}
