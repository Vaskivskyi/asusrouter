"""Result of processing hook_007.content."""

from asusrouter import AsusData
from asusrouter.modules.connection import ConnectionState
from asusrouter.modules.wireguard import AsusWireGuardServer

expected_result = {
    AsusData.WIREGUARD_SERVER: {
        1: {
            "state": AsusWireGuardServer.ON,
            "lan_access": True,
            "address": "10.1.0.1/24",
            "port": 443,
            "dns": True,
            "nat6": True,
            "psk": True,
            "keep_alive": 25,
            "private_key": "PrIvAtE KeY",
            "public_key": "PuBlIk kEy",
            "clients": {
                1: {
                    "enabled": True,
                    "name": "FakeName001",
                    "address": "10.1.0.2/32",
                    "allowed_ips": ["10.1.0.2/32"],
                    "client_allowed_ips": ["192.168.1.0/24", "10.1.0.0/24"],
                    "state": ConnectionState.DISCONNECTED,
                },
                2: {
                    "enabled": True,
                    "name": "FakeName002",
                    "address": "10.1.0.3/32",
                    "allowed_ips": ["10.1.0.3/32"],
                    "client_allowed_ips": ["192.168.1.0/24", "10.1.0.0/24"],
                    "state": ConnectionState.DISCONNECTED,
                },
                3: {
                    "enabled": True,
                    "name": "FakeName003",
                    "address": "10.1.0.4/32",
                    "allowed_ips": ["10.1.0.4/32"],
                    "client_allowed_ips": ["192.168.1.0/24", "10.1.0.0/24"],
                    "state": ConnectionState.DISCONNECTED,
                },
                4: {
                    "enabled": True,
                    "name": "FakeName004",
                    "address": "10.1.0.5/32",
                    "allowed_ips": ["10.1.0.5/32"],
                    "client_allowed_ips": ["192.168.1.0/24", "10.1.0.0/24"],
                    "state": ConnectionState.DISCONNECTED,
                },
                5: {
                    "enabled": True,
                    "name": "FakeName005",
                    "address": "10.1.0.6/32",
                    "allowed_ips": ["10.1.0.6/32"],
                    "client_allowed_ips": ["192.168.1.0/24", "10.1.0.0/24"],
                    "state": ConnectionState.DISCONNECTED,
                },
                6: {
                    "enabled": True,
                    "name": "FakeName006",
                    "address": "10.1.0.7/32",
                    "allowed_ips": ["10.1.0.7/32"],
                    "client_allowed_ips": ["192.168.1.0/24", "10.1.0.0/24"],
                    "state": ConnectionState.DISCONNECTED,
                },
            },
        }
    }
}
