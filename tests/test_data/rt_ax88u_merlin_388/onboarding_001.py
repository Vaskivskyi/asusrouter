"""Result of processing onboarding_001.content."""

from asusrouter import AsusData
from asusrouter.modules.aimesh import AiMeshDevice

expected_result = {
    AsusData.AIMESH: {
        "00:00:00:00:00:00": AiMeshDevice(
            status=True,
            alias="Living Room",
            model="RT-AX88U",
            product_id="RT-AX88U",
            ip="192.168.1.1",
            fw="3.0.0.4.388.4_0",
            fw_new=None,
            mac="00:00:00:00:00:00",
            ap={"2ghz": "00:00:00:00:00:00", "5ghz": "00:00:00:00:00:01"},
            parent={},
            type="router",
            level=0,
            config={},
        )
    },
    AsusData.CLIENTS: {
        "00:00:00:00:00:02": {
            "connection_type": 1,
            "guest": 0,
            "ip": "192.168.1.2",
            "mac": "00:00:00:00:00:02",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": "-34",
        },
        "00:00:00:00:00:03": {
            "connection_type": 1,
            "guest": 0,
            "ip": "192.168.1.3",
            "mac": "00:00:00:00:00:03",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": "-47",
        },
        "00:00:00:00:00:04": {
            "connection_type": 1,
            "guest": 0,
            "ip": "192.168.1.4",
            "mac": "00:00:00:00:00:04",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": "-58",
        },
        "00:00:00:00:00:05": {
            "connection_type": 1,
            "guest": 0,
            "ip": "192.168.1.5",
            "mac": "00:00:00:00:00:05",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": "-50",
        },
        "00:00:00:00:00:06": {
            "connection_type": 1,
            "guest": 0,
            "ip": "192.168.1.6",
            "mac": "00:00:00:00:00:06",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": "-26",
        },
        "00:00:00:00:00:07": {
            "connection_type": 1,
            "guest": 0,
            "ip": "192.168.1.7",
            "mac": "00:00:00:00:00:07",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": "-52",
        },
        "00:00:00:00:00:08": {
            "connection_type": 1,
            "guest": 0,
            "ip": "192.168.1.8",
            "mac": "00:00:00:00:00:08",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": "-41",
        },
        "00:00:00:00:00:09": {
            "connection_type": 1,
            "guest": 0,
            "ip": "192.168.1.9",
            "mac": "00:00:00:00:00:09",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": "-41",
        },
        "00:00:00:00:00:10": {
            "connection_type": 1,
            "guest": 0,
            "ip": "192.168.1.10",
            "mac": "00:00:00:00:00:10",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": "-44",
        },
        "00:00:00:00:00:11": {
            "connection_type": 1,
            "guest": 0,
            "ip": "192.168.1.11",
            "mac": "00:00:00:00:00:11",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": "-43",
        },
        "00:00:00:00:00:12": {
            "connection_type": 1,
            "guest": 0,
            "ip": "192.168.1.12",
            "mac": "00:00:00:00:00:12",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": "-53",
        },
        "00:00:00:00:00:13": {
            "connection_type": 2,
            "guest": 0,
            "ip": "192.168.1.13",
            "mac": "00:00:00:00:00:13",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": "-43",
        },
        "00:00:00:00:00:14": {
            "connection_type": 2,
            "guest": 0,
            "ip": "192.168.1.14",
            "mac": "00:00:00:00:00:14",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": "-27",
        },
        "00:00:00:00:00:15": {
            "connection_type": 2,
            "guest": 0,
            "ip": "192.168.1.15",
            "mac": "00:00:00:00:00:15",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": "-40",
        },
        "00:00:00:00:00:16": {
            "connection_type": 0,
            "guest": 0,
            "ip": "192.168.1.16",
            "mac": "00:00:00:00:00:16",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": None,
        },
        "00:00:00:00:00:17": {
            "connection_type": 0,
            "guest": 0,
            "ip": "192.168.1.17",
            "mac": "00:00:00:00:00:17",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": None,
        },
        "00:00:00:00:00:18": {
            "connection_type": 0,
            "guest": 0,
            "ip": "192.168.1.18",
            "mac": "00:00:00:00:00:18",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": None,
        },
        "00:00:00:00:00:19": {
            "connection_type": 0,
            "guest": 0,
            "ip": "192.168.1.19",
            "mac": "00:00:00:00:00:19",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": None,
        },
        "00:00:00:00:00:20": {
            "connection_type": 0,
            "guest": 0,
            "ip": "192.168.1.20",
            "mac": "00:00:00:00:00:20",
            "node": "00:00:00:00:00:00",
            "online": True,
            "rssi": None,
        },
    },
}
