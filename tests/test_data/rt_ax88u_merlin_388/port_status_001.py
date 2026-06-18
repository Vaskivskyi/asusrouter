"""Result of processing port_status_001.content."""

from __future__ import annotations

from asusrouter import AsusData
from asusrouter.modules.ports import (
    ARPortCapability,
    ARPortEthernetSpeed,
    ARPortType,
    ARPortUSBSpeed,
)

expected_result = {
    AsusData.NODE_INFO: {
        "00:00:00:00:00:00": {"cd_good_to_go": "1"},
    },
    AsusData.PORTS: {
        "00:00:00:00:00:00": {
            ARPortType.LAN: {
                1: {
                    "capabilities": [ARPortCapability.LAN],
                    "id": 1,
                    "max_rate": ARPortEthernetSpeed.MBPS_1000,
                    "link_rate": ARPortEthernetSpeed.MBPS_1000,
                    "state": True,
                },
                2: {
                    "capabilities": [ARPortCapability.LAN],
                    "id": 2,
                    "max_rate": ARPortEthernetSpeed.MBPS_1000,
                    "link_rate": ARPortEthernetSpeed.MBPS_1000,
                    "state": True,
                },
                3: {
                    "capabilities": [ARPortCapability.LAN],
                    "id": 3,
                    "max_rate": ARPortEthernetSpeed.MBPS_1000,
                    "link_rate": ARPortEthernetSpeed.MBPS_1000,
                    "state": True,
                },
                4: {
                    "capabilities": [ARPortCapability.LAN],
                    "id": 4,
                    "max_rate": ARPortEthernetSpeed.MBPS_1000,
                    "link_rate": ARPortEthernetSpeed.DOWN,
                    "state": False,
                },
                5: {
                    "capabilities": [ARPortCapability.LAN],
                    "id": 5,
                    "max_rate": ARPortEthernetSpeed.MBPS_1000,
                    "link_rate": ARPortEthernetSpeed.DOWN,
                    "state": False,
                },
                6: {
                    "capabilities": [ARPortCapability.LAN],
                    "id": 6,
                    "max_rate": ARPortEthernetSpeed.MBPS_1000,
                    "link_rate": ARPortEthernetSpeed.DOWN,
                    "state": False,
                },
                7: {
                    "capabilities": [ARPortCapability.LAN],
                    "id": 7,
                    "max_rate": ARPortEthernetSpeed.MBPS_1000,
                    "link_rate": ARPortEthernetSpeed.DOWN,
                    "state": False,
                },
                8: {
                    "capabilities": [ARPortCapability.LAN],
                    "id": 8,
                    "max_rate": ARPortEthernetSpeed.MBPS_1000,
                    "link_rate": ARPortEthernetSpeed.MBPS_1000,
                    "state": True,
                },
            },
            ARPortType.USB: {
                1: {
                    "capabilities": [ARPortCapability.USB],
                    "devices": None,
                    "id": 1,
                    "max_rate": ARPortUSBSpeed.USB3,
                    "link_rate": ARPortUSBSpeed.DOWN,
                    "modem": False,
                    "state": False,
                },
                2: {
                    "capabilities": [ARPortCapability.USB],
                    "devices": None,
                    "id": 2,
                    "max_rate": ARPortUSBSpeed.USB3,
                    "link_rate": ARPortUSBSpeed.DOWN,
                    "modem": False,
                    "state": False,
                },
            },
            ARPortType.WAN: {
                0: {
                    "capabilities": [
                        ARPortCapability.WAN,
                        ARPortCapability.DUALWAN_PRIMARY,
                    ],
                    "id": 0,
                    "max_rate": ARPortEthernetSpeed.MBPS_1000,
                    "link_rate": ARPortEthernetSpeed.MBPS_1000,
                    "state": True,
                }
            },
        },
    },
}
