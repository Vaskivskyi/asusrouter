"""Result of processing hook_001.content."""

from __future__ import annotations

from asusrouter import AsusData

expected_result = {
    AsusData.NETWORK: {
        "wan": {"rx": 63243891966, "tx": 9258317413},
        "wired": {"rx": 15533318508, "tx": 34569805498},
        "bridge": {"rx": 13053422522, "tx": 82894153490},
        "2ghz": {"rx": 487166238, "tx": 1628373444},
        "5ghz": {"rx": 794233169, "tx": 13670431628},
        "lacp1": {"rx": 0, "tx": 1587313292},
        "lacp2": {"rx": 4121988120, "tx": 71338048},
    },
}
