"""Result of processing hook_005.content."""

from asusrouter import AsusData
from asusrouter.modules.endpoint.error import AccessError
from asusrouter.modules.vpnc import AsusVPNC, AsusVPNType

expected_result = {
    AsusData.OPENVPN_CLIENT: {
        1: {"state": AsusVPNC.UNKNOWN, "error": AccessError.NO_ERROR},
        2: {"state": AsusVPNC.UNKNOWN, "error": AccessError.NO_ERROR},
        3: {"state": AsusVPNC.UNKNOWN, "error": AccessError.NO_ERROR},
        4: {"state": AsusVPNC.UNKNOWN, "error": AccessError.NO_ERROR},
        5: {"state": AsusVPNC.UNKNOWN, "error": AccessError.NO_ERROR},
    },
    AsusData.VPNC: {
        AsusVPNType.L2TP: {},
        AsusVPNType.OPENVPN: {
            1: {"state": AsusVPNC.UNKNOWN, "error": AccessError.NO_ERROR},
            2: {"state": AsusVPNC.UNKNOWN, "error": AccessError.NO_ERROR},
            3: {"state": AsusVPNC.UNKNOWN, "error": AccessError.NO_ERROR},
            4: {"state": AsusVPNC.UNKNOWN, "error": AccessError.NO_ERROR},
            5: {"state": AsusVPNC.UNKNOWN, "error": AccessError.NO_ERROR},
        },
        AsusVPNType.PPTP: {},
        AsusVPNType.SURFSHARK: {},
        AsusVPNType.WIREGUARD: {
            5: {
                "state": True,
                "nat": True,
                "private_key": "PrIvAtE KeY",
                "address": "10.1.1.11/32",
                "public_key": "PuBlIk kEy",
                "psk": "PrE-ShArEd kEy",
                "allowed_ips": ["10.1.1.0/24", "192.168.1.0/24"],
                "endpoint_address": "111.222.111.222",
                "endpoint_port": 443,
                "keep_alive": 25,
            },
            1: {"state": AsusVPNC.UNKNOWN, "error": AccessError.NO_ERROR},
            2: {"state": AsusVPNC.UNKNOWN, "error": AccessError.NO_ERROR},
            3: {"state": AsusVPNC.UNKNOWN, "error": AccessError.NO_ERROR},
            4: {"state": AsusVPNC.UNKNOWN, "error": AccessError.NO_ERROR},
        },
    },
    AsusData.VPNC_CLIENTLIST: "",
    AsusData.WIREGUARD_CLIENT: {
        5: {
            "state": True,
            "nat": True,
            "private_key": "PrIvAtE KeY",
            "address": "10.1.1.11/32",
            "public_key": "PuBlIk kEy",
            "psk": "PrE-ShArEd kEy",
            "allowed_ips": ["10.1.1.0/24", "192.168.1.0/24"],
            "endpoint_address": "111.222.111.222",
            "endpoint_port": 443,
            "keep_alive": 25,
        },
        1: {"state": AsusVPNC.UNKNOWN, "error": AccessError.NO_ERROR},
        2: {"state": AsusVPNC.UNKNOWN, "error": AccessError.NO_ERROR},
        3: {"state": AsusVPNC.UNKNOWN, "error": AccessError.NO_ERROR},
        4: {"state": AsusVPNC.UNKNOWN, "error": AccessError.NO_ERROR},
    },
}
