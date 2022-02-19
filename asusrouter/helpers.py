"""Helpers module"""

import json
import logging
import re
import xmltodict
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)


# These values are just stored directly in this order in the corresponding node
DEVICEMAP_BY_INDEX = {
    "WAN": {
        "wan": [
            "status",
            "sbstatus",
            "auxstatus",
        ],
    },
    "WAN0": {
        "first_wan": [
            "status",
            "sbstatus",
            "auxstatus",
        ],
    },
    "WAN1": {
        "second_wan": [
            "status",
            "sbstatus",
            "auxstatus",
        ],
    },
    "USB": {
        "usb": [
            "status",
        ]
    }
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
    "VPN": {
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
    "SYS": {
        "sys": [
            "uptimeStr",
        ],
    },
    "QTN": {
        "qtn": [
            "qtn_state",
        ],
    },
    "USB": {
        "usb": [
            "modem_enable",
        ],
    },
    "WAN0": {
        "wan": [
            "wan0_enable",
            "wan0_realip_state",
            "wan0_ipaddr",
            "wan0_realip_ip",
        ],
    },
    "WAN1": {
        "wan": [
            "wan1_enable",
            "wan1_realip_state",
            "wan1_ipaddr",
            "wan1_realip_ip",
        ],
    },
    "SIM": {
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
    "DHCP": {
        "dhcp": [
            "dnsqmode",
        ],
    },
    "DIAG": {
        "diag": [
            "diag_dblog_enable",
            "diag_dblog_remaining",
        ]
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


async def async_convert_to_json(text : str) -> dict:
    """Fix JSON conversion for known pages"""

    data = re.sub('\s+','',text)

    if "get_wan_lan_status=" in data:
        data = data.replace("get_wan_lan_status=", "")
        data = data[:-1]
    elif "varcpuInfo,memInfo=newObject();cpuInfo=" in data:
        data = data.replace("varcpuInfo,memInfo=newObject();cpuInfo=", '{"cpu":{')
        data = data.replace(";memInfo=", '},"memory":{')
        data = data.replace(";", "}}")
    else:
        _LOGGER.error("Unknown data. Template for this data is unknown")
        return {}
    
    return json.loads(data.encode().decode('utf-8-sig') )

async def async_convert_xml(text : str) -> dict:
    """Obtain data from XML"""

    data = xmltodict.parse(text)
    if 'devicemap' in data:
        return await async_parse_devicemap(data['devicemap'])

    return {}

async def async_parse_devicemap(devicemap : dict) -> dict:
    """Parse devicemap"""

    data = {}

    # Get values only with index
    for node in DEVICEMAP_BY_INDEX:
        _node = {}
        for key in DEVICEMAP_BY_INDEX[node]:
            for el in range(len(DEVICEMAP_BY_INDEX[node][key])):
                _node[DEVICEMAP_BY_INDEX[node][key][el]] = devicemap[key][el]
            del devicemap[key][0 : (len(DEVICEMAP_BY_INDEX[node][key]) - 1)]
        data[node] = _node

    # Get values by key
    for node in DEVICEMAP_GENERAL:
        _node = {}
        for key in DEVICEMAP_GENERAL[node]:
            for el in DEVICEMAP_GENERAL[node][key]:
                if type(devicemap[key]) == str:
                    if el in devicemap[key]:
                        _node[el] = devicemap[key].replace("{}=".format(el), "")
                        break
                else:
                    for value in devicemap[key]:
                        if el in value:
                            _node[el] = value.replace("{}=".format(el), "")
                            break
        if node in data:
            data[node].update(_node)
        else:
            data[node] = _node

    # Clear values from useless symbols
    for node in DEVICEMAP_CLEAR:
        for value in DEVICEMAP_CLEAR[node]:
            data[node][value] = data[node][value].replace(DEVICEMAP_CLEAR[node][value], "")

    return data

async def async_parse_uptime(data : str) -> datetime:
    """Parse uptime to get boot time"""

    part = data.split("(")
    seconds = int(re.search("([0-9]+)", part[1]).group())
    when = datetime.strptime(part[0], "%a, %d %b %Y %H:%M:%S %z")

    boot = when - timedelta(seconds = seconds)

    return boot


async def async_transform_port_speed(value : str | None = None) -> int | None:
    """Transform port speed from the text value to actual speed in Mb/s"""

    if value is None:
        return None
    elif value == "X":
        return 0
    elif value == "M":
        return 100
    elif value == "G":
        return 1000
    else:
        raise NotImplementedError("Conversion for this value is not implemented")

