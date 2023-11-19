"""Result of processing ethernet_ports_001.content."""

from asusrouter import AsusData
from asusrouter.modules.ports import PortSpeed, PortType

expected_result = {
    AsusData.PORTS: {
        PortType.LAN: {
            1: {
                "link_rate": PortSpeed.LINK_1000,
                "state": True,
            },
            2: {
                "link_rate": PortSpeed.LINK_1000,
                "state": True,
            },
            3: {
                "link_rate": PortSpeed.LINK_1000,
                "state": True,
            },
            4: {
                "link_rate": PortSpeed.LINK_DOWN,
                "state": False,
            },
            5: {
                "link_rate": PortSpeed.LINK_DOWN,
                "state": False,
            },
            6: {
                "link_rate": PortSpeed.LINK_DOWN,
                "state": False,
            },
            7: {
                "link_rate": PortSpeed.LINK_DOWN,
                "state": False,
            },
            8: {
                "link_rate": PortSpeed.LINK_1000,
                "state": True,
            },
        },
        PortType.WAN: {
            0: {
                "link_rate": PortSpeed.LINK_1000,
                "state": True,
            },
        },
    }
}
