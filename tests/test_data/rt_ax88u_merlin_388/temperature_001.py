"""Result of processing firmware_001.content."""

from asusrouter import AsusData
from asusrouter.modules.wlan import Wlan

expected_result = {
    AsusData.TEMPERATURE: {
        Wlan.FREQ_2G: 44.0,
        Wlan.FREQ_5G: 44.0,
        "cpu": 65.514,
    }
}
