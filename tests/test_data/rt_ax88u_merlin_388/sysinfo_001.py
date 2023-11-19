"""Result of processing sysinfo_001.content."""

from asusrouter import AsusData
from asusrouter.modules.wlan import Wlan

expected_result = {
    AsusData.SYSINFO: {
        "wlan": {
            Wlan.FREQ_2G: {
                "client_associated": 11,
                "client_authorized": 11,
                "client_authenticated": 11,
            },
            Wlan.FREQ_5G: {
                "client_associated": 3,
                "client_authorized": 3,
                "client_authenticated": 3,
            },
            Wlan.FREQ_5G2: {
                "client_associated": 0,
                "client_authorized": 0,
                "client_authenticated": 0,
            },
            Wlan.FREQ_6G: {
                "client_associated": 0,
                "client_authorized": 0,
                "client_authenticated": 0,
            },
        },
        "connections": {"total": 320, "active": 86},
        "memory": {
            "total": 882.34,
            "free": 240.57,
            "buffers": 0.0,
            "cache": 52.73,
            "swap_1": 0.0,
            "swap_2": 0.0,
            "nvram": 85328,
            "jffs_used": 7.49,
            "jffs_total": 63.0,
        },
        "load_avg": {1: 1.98, 5: 2.04, 15: 2.01},
    }
}
