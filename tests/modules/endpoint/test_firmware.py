"""Tests for the Firmware endpoint module."""

from typing import Any

from asusrouter.modules.data import AsusData
from asusrouter.modules.endpoint.firmware import process, read
from asusrouter.modules.firmware import (
    Firmware,
    WebsError,
    WebsFlag,
    WebsUpdate,
    WebsUpgrade,
)
from asusrouter.tools.readers import read_js_variables
import pytest


def test_read() -> None:
    """Test read function."""

    # Check if 'read' is the same as 'read_js_variables'
    assert read == read_js_variables


# Case 1: No input
# Check the default values and make sure that
# the function does not crash even on no input.
test_case_1_input: dict[str, Any] = {}
test_case_1: dict[str, Any] = {
    "current": None,
    "state": False,
    "available": None,
    "state_beta": False,
    "available_beta": None,
    "webs": {
        "update": WebsUpdate.UNKNOWN,
        "upgrade": WebsUpgrade.INACTIVE,
        "available": None,
        "available_beta": None,
        "required": None,
        "error": WebsError.UNKNOWN,
        "flag": WebsFlag.UNKNOWN,
        "level": None,
    },
    "cfg": {
        "check": None,
        "upgrade": None,
    },
    "sig": {
        "update": None,
        "upgrade": None,
        "version": None,
        "error": None,
        "flag": None,
    },
    "hndwr": {
        "status": None,
    },
}

# Case 2: Stable firmware available
# Check that a stable available firmware is properly
# processed and reported as available update.
test_case_2_input: dict[str, Any] = {
    "webs_state_info": "3.0.0.4.388.8_0",
    "firmware": Firmware("3.0.0.4.388.7_0"),
}

test_case_2 = test_case_1.copy()
test_case_2_webs = test_case_2["webs"].copy()
test_case_2_webs.update(
    {
        "available": Firmware("3.0.0.4.388.8_0"),
    }
)
test_case_2.update(
    {
        "current": Firmware("3.0.0.4.388.7_0"),
        "state": True,
        "available": Firmware("3.0.0.4.388.8_0"),
        "webs": test_case_2_webs,
    }
)

# Case 3: Beta firmware available
# Check that a beta available firmware is properly
# processed and reported as available update.
test_case_3_input: dict[str, Any] = {
    "webs_state_info": "3.0.0.4.388.8_0",
    "webs_state_info_beta": "3.0.0.4.388.8_2beta1",
    "firmware": Firmware("3.0.0.4.388.8_0"),
}

test_case_3 = test_case_1.copy()
test_case_3_webs = test_case_3["webs"].copy()
test_case_3_webs.update(
    {
        "available": Firmware("3.0.0.4.388.8_0"),
        "available_beta": Firmware("3.0.0.4.388.8_2beta1"),
    }
)
test_case_3.update(
    {
        "current": Firmware("3.0.0.4.388.8_0"),
        "state_beta": True,
        "available_beta": Firmware("3.0.0.4.388.8_2beta1"),
        "webs": test_case_3_webs,
    }
)

# Case 4: Stable and beta firmware available
# Check that both stable and beta available firmware are
# properly processed and reported as available updates.
test_case_4_input: dict[str, Any] = {
    "webs_state_info": "3.0.0.4.388.8_0",
    "webs_state_info_beta": "3.0.0.4.388.8_2beta1",
    "firmware": Firmware("3.0.0.4.388.7_0"),
}

test_case_4 = test_case_1.copy()
test_case_4_webs = test_case_4["webs"].copy()
test_case_4_webs.update(
    {
        "available": Firmware("3.0.0.4.388.8_0"),
        "available_beta": Firmware("3.0.0.4.388.8_2beta1"),
    }
)
test_case_4.update(
    {
        "current": Firmware("3.0.0.4.388.7_0"),
        "state": True,
        "available": Firmware("3.0.0.4.388.8_0"),
        "state_beta": True,
        "available_beta": Firmware("3.0.0.4.388.8_2beta1"),
        "webs": test_case_4_webs,
    }
)

# Case 5: ROG flag (Merlin firmware)
# Check that the ROG flag is properly ignored.
test_case_5_input: dict[str, Any] = {
    "webs_state_info": "3.0.0.4.388.7_0",
    "firmware": Firmware("3.0.0.4.388.7_0_rog"),
}

test_case_5 = test_case_1.copy()
test_case_5_webs = test_case_5["webs"].copy()
test_case_5_webs.update(
    {
        "available": Firmware("3.0.0.4.388.7_0"),
    }
)
test_case_5.update(
    {
        "current": Firmware("3.0.0.4.388.7_0_rog"),
        "webs": test_case_5_webs,
    }
)

# Case 6: Rog flag reversed (Merlin firmware)
# Check that the ROG flag is properly ignored.
test_case_6_input: dict[str, Any] = {
    "webs_state_info": "3.0.0.4.388.7_0_rog",
    "firmware": Firmware("3.0.0.4.388.7_0"),
}

test_case_6 = test_case_1.copy()
test_case_6_webs = test_case_6["webs"].copy()
test_case_6_webs.update(
    {
        "available": Firmware("3.0.0.4.388.7_0_rog"),
    }
)
test_case_6.update(
    {
        "current": Firmware("3.0.0.4.388.7_0"),
        "webs": test_case_6_webs,
    }
)


test_cases = [
    (
        test_case_1_input,
        {AsusData.FIRMWARE: test_case_1},
    ),
    (
        test_case_2_input,
        {AsusData.FIRMWARE: test_case_2},
    ),
    (
        test_case_3_input,
        {AsusData.FIRMWARE: test_case_3},
    ),
    (
        test_case_4_input,
        {AsusData.FIRMWARE: test_case_4},
    ),
    (
        test_case_5_input,
        {AsusData.FIRMWARE: test_case_5},
    ),
    (
        test_case_6_input,
        {AsusData.FIRMWARE: test_case_6},
    ),
]


@pytest.mark.parametrize(("input_data", "expected"), test_cases)
def test_process(input_data: dict[str, Any], expected: dict[str, Any]) -> None:
    """Test process function."""

    result = process(input_data)
    assert result == expected
