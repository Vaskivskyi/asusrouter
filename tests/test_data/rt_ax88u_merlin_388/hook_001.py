"""Result of processing hook_001.content."""

from asusrouter import AsusData

expected_result = {
    AsusData.CPU: {
        "total": {"total": 210386498.0, "used": 10006747.0},
        1: {"total": 52557468, "used": 4733197},
        2: {"total": 52587131, "used": 1731814},
        3: {"total": 52621020, "used": 1821047},
        4: {"total": 52620879, "used": 1720689},
    },
    AsusData.NETWORK: {
        "wan": {"rx": 63243891966, "tx": 9258317413},
        "wired": {"rx": 15533318508, "tx": 34569805498},
        "bridge": {"rx": 13053422522, "tx": 82894153490},
        "2ghz": {"rx": 487166238, "tx": 1628373444},
        "5ghz": {"rx": 794233169, "tx": 13670431628},
        "lacp1": {"rx": 0, "tx": 1587313292},
        "lacp2": {"rx": 4121988120, "tx": 71338048},
    },
    AsusData.RAM: {
        "free": 235464,
        "total": 1048576,
        "used": 813112,
        "usage": 77.54,
    },
}
