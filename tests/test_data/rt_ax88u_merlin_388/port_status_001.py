"""Result of processing port_status_001.content."""

from asusrouter import AsusData
from asusrouter.modules.ports import (
    PortCapability,
    PortSpeed,
    PortType,
    USBSpeed,
)

expected_result = {
    AsusData.NODE_INFO: {
        "00:00:00:00:00:00": {"cd_good_to_go": "1"},
    },
    AsusData.PORTS: {
        "00:00:00:00:00:00": {
            PortType.LAN: {
                1: {
                    "capabilities": [PortCapability.LAN],
                    "id": 1,
                    "max_rate": PortSpeed.LINK_1000,
                    "link_rate": PortSpeed.LINK_1000,
                    "state": True,
                },
                2: {
                    "capabilities": [PortCapability.LAN],
                    "id": 2,
                    "max_rate": PortSpeed.LINK_1000,
                    "link_rate": PortSpeed.LINK_1000,
                    "state": True,
                },
                3: {
                    "capabilities": [PortCapability.LAN],
                    "id": 3,
                    "max_rate": PortSpeed.LINK_1000,
                    "link_rate": PortSpeed.LINK_1000,
                    "state": True,
                },
                4: {
                    "capabilities": [PortCapability.LAN],
                    "id": 4,
                    "max_rate": PortSpeed.LINK_1000,
                    "link_rate": PortSpeed.LINK_DOWN,
                    "state": False,
                },
                5: {
                    "capabilities": [PortCapability.LAN],
                    "id": 5,
                    "max_rate": PortSpeed.LINK_1000,
                    "link_rate": PortSpeed.LINK_DOWN,
                    "state": False,
                },
                6: {
                    "capabilities": [PortCapability.LAN],
                    "id": 6,
                    "max_rate": PortSpeed.LINK_1000,
                    "link_rate": PortSpeed.LINK_DOWN,
                    "state": False,
                },
                7: {
                    "capabilities": [PortCapability.LAN],
                    "id": 7,
                    "max_rate": PortSpeed.LINK_1000,
                    "link_rate": PortSpeed.LINK_DOWN,
                    "state": False,
                },
                8: {
                    "capabilities": [PortCapability.LAN],
                    "id": 8,
                    "max_rate": PortSpeed.LINK_1000,
                    "link_rate": PortSpeed.LINK_1000,
                    "state": True,
                },
            },
            PortType.USB: {
                1: {
                    "capabilities": [PortCapability.USB],
                    "devices": None,
                    "id": 1,
                    "max_rate": USBSpeed.USB_30,
                    "link_rate": USBSpeed.USB_DOWN,
                    "modem": False,
                    "state": False,
                },
                2: {
                    "capabilities": [PortCapability.USB],
                    "devices": None,
                    "id": 2,
                    "max_rate": USBSpeed.USB_30,
                    "link_rate": USBSpeed.USB_DOWN,
                    "modem": False,
                    "state": False,
                },
            },
            PortType.WAN: {
                0: {
                    "capabilities": [
                        PortCapability.WAN,
                        PortCapability.DUALWAN_PRIMARY,
                    ],
                    "id": 0,
                    "max_rate": PortSpeed.LINK_1000,
                    "link_rate": PortSpeed.LINK_1000,
                    "state": True,
                }
            },
        },
    },
}
