"""Result of processing network_001.content."""

from asusrouter import AsusData

expected_result = {
    AsusData.PING: {
        "result": [{"loss": "0", "ping": "7.294", "jitter": "7.294"}]
    }
}
