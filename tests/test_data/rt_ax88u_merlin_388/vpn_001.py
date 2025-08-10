"""Result of processing vpn_001.content."""

from asusrouter import AsusData
from asusrouter.modules.openvpn import AsusOVPNClient, AsusOVPNServer

expected_result = {
    AsusData.OPENVPN_CLIENT: {
        1: {"state": AsusOVPNClient.DISCONNECTED},
        2: {"state": AsusOVPNClient.DISCONNECTED},
        3: {"state": AsusOVPNClient.DISCONNECTED},
        4: {"state": AsusOVPNClient.DISCONNECTED},
        5: {"state": AsusOVPNClient.DISCONNECTED},
    },
    AsusData.OPENVPN_SERVER: {
        1: {
            "client_list": [],
            "routing_table": [],
            "state": AsusOVPNServer.CONNECTED,
        },
        2: {"state": AsusOVPNServer.DISCONNECTED},
    },
}
