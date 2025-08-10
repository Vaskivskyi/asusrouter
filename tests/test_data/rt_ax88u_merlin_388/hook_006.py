"""Result of processing hook_006.content."""

# ruff: noqa: S104

from asusrouter import AsusData
from asusrouter.modules.connection import ConnectionState, ConnectionStatus
from asusrouter.modules.endpoint.wan import AsusDualWAN
from asusrouter.modules.ip_address import IPAddressType

expected_result = {
    AsusData.WAN: {
        "internet": {
            "unit": 0,
            "link": ConnectionStatus.CONNECTED,
            "ip_address": "111.222.111.222",
        },
        0: {
            "auxstate": ConnectionStatus.DISCONNECTED,
            "primary": True,
            "protocol": IPAddressType.PPPOE,
            "real_ip": "111.222.111.222",
            "real_ip_state": None,
            "state": ConnectionStatus.CONNECTED,
            "bstate": ConnectionStatus.DISCONNECTED,
            "main": {
                "dns": ["222.111.222.110", "222.111.222.111"],
                "expires": None,
                "gateway": "111.222.111.1",
                "ip_address": "111.222.111.222",
                "lease": None,
                "mask": "255.255.255.255",
            },
            "extra": {
                "dns": ["192.168.1.254"],
                "expires": 604829,
                "gateway": "192.168.1.254",
                "ip_address": "192.168.1.2",
                "lease": 86400,
                "mask": "255.255.255.0",
            },
            "link": ConnectionState.CONNECTED,
        },
        1: {
            "auxstate": ConnectionStatus.DISCONNECTED,
            "primary": False,
            "protocol": IPAddressType.DHCP,
            "real_ip": "",
            "real_ip_state": False,
            "state": ConnectionStatus.DISCONNECTED,
            "bstate": ConnectionStatus.DISCONNECTED,
            "main": {
                "dns": [],
                "expires": None,
                "gateway": "0.0.0.0",
                "ip_address": "0.0.0.0",
                "lease": None,
                "mask": "0.0.0.0",
            },
            "extra": {
                "dns": [],
                "expires": None,
                "gateway": "0.0.0.0",
                "ip_address": "0.0.0.0",
                "lease": None,
                "mask": "0.0.0.0",
            },
            "link": ConnectionState.DISCONNECTED,
        },
        "aggregation": {"state": False, "ports": ["4", "0"]},
        "dualwan": {
            "mode": AsusDualWAN.FAILOVER,
            "priority": ["wan", None],
            "state": False,
        },
    }
}
