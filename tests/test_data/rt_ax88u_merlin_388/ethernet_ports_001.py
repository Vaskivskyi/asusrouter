"""Result of processing ethernet_ports_001.content."""

from __future__ import annotations

from asusrouter import AsusData
from asusrouter.modules.ports import ARPortEthernetSpeed, ARPortType

expected_result = {
    AsusData.PORTS: {
        ARPortType.LAN: {
            1: {
                "link_rate": ARPortEthernetSpeed.MBPS_1000,
                "state": True,
            },
            2: {
                "link_rate": ARPortEthernetSpeed.MBPS_1000,
                "state": True,
            },
            3: {
                "link_rate": ARPortEthernetSpeed.MBPS_1000,
                "state": True,
            },
            4: {
                "link_rate": ARPortEthernetSpeed.DOWN,
                "state": False,
            },
            5: {
                "link_rate": ARPortEthernetSpeed.DOWN,
                "state": False,
            },
            6: {
                "link_rate": ARPortEthernetSpeed.DOWN,
                "state": False,
            },
            7: {
                "link_rate": ARPortEthernetSpeed.DOWN,
                "state": False,
            },
            8: {
                "link_rate": ARPortEthernetSpeed.MBPS_1000,
                "state": True,
            },
        },
        ARPortType.WAN: {
            0: {
                "link_rate": ARPortEthernetSpeed.MBPS_1000,
                "state": True,
            },
        },
    }
}
