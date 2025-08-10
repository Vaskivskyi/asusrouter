"""Tests for the onboarding endpoint module."""

from typing import Any
from unittest.mock import patch

from asusrouter import AsusData
from asusrouter.modules.aimesh import AiMeshDevice
from asusrouter.modules.endpoint.onboarding import (
    CONNECTION_TYPE,
    process,
    process_aimesh_node,
    process_connection,
    read,
    read_preprocess,
)
import pytest

CONTENT_RAW = (
    "get_onboardinglist = [{}][0];\n"
    "get_cfg_clientlist = [[{}]][0];\n"
    "get_onboardingstatus = [{}][0];\n"
    "get_wclientlist = [{}][0];\n"
    "get_wiredclientlist = [{}][0];\n"
    "get_allclientlist = [{}][0];\n"
    'cfg_note = "1";\n'
    'cfg_obre = "";\n'
    "\n"
    "\n"
)

CONTENT_PREPROCESSED = (
    '{"get_onboardinglist":[{}],'
    '"get_cfg_clientlist":[[{}]],'
    '"get_onboardingstatus":[{}],'
    '"get_wclientlist":[{}],'
    '"get_wiredclientlist":[{}],'
    '"get_allclientlist":[{}],'
    '"cfg_note":"1",'
    '"cfg_obre":""}'
)

CONTENT_READ = {
    "get_onboardinglist": [{}],
    "get_cfg_clientlist": [[{}]],
    "get_onboardingstatus": [{}],
    "get_wclientlist": [{}],
    "get_wiredclientlist": [{}],
    "get_allclientlist": [{}],
    "cfg_note": "1",
    "cfg_obre": "",
}


def test_read() -> None:
    """Test read function."""

    with (
        patch(
            "asusrouter.modules.endpoint.onboarding.read_preprocess",
            return_value=CONTENT_PREPROCESSED,
        ) as mock_preprocess,
        patch(
            "asusrouter.modules.endpoint.onboarding.read_json_content",
            return_value=CONTENT_READ,
        ) as mock_read_json_content,
    ):
        # Get the result
        result = read(CONTENT_RAW)

        # Check the result
        assert result == CONTENT_READ

        # Check the calls
        mock_preprocess.assert_called_once_with(CONTENT_RAW)
        mock_read_json_content.assert_called_once_with(CONTENT_PREPROCESSED)


def test_read_preprocess() -> None:
    """Test read_preprocess function."""

    # Get the result
    result = read_preprocess(CONTENT_RAW)

    # Check the result
    assert result == CONTENT_PREPROCESSED


DATA_CLIENTLIST = [[{"mac": "00:aa:11:bb:22:cc", "ip": "192.168.1.1"}]]
DATA_ALLCLIENTLIST = [
    {
        "00:aa:11:bb:22:cc": {
            "2G": {"00:aa:11:bb:22:dd": {"ip": "192.168.1.12", "rssi": -34}}
        }
    }
]

RESULT_CLIENTLIST = {
    "00:aa:11:bb:22:cc": AiMeshDevice(
        status=False,
        alias=None,
        model=None,
        product_id=None,
        ip="192.168.1.1",
        fw=None,
        fw_new=None,
        mac="00:aa:11:bb:22:cc",
        ap={},
        parent={},
        type="router",
        level=0,
        config=None,
    ),
}

RESULT_ALLCLIENTLIST = {
    "00:aa:11:bb:22:dd": {
        "connection_type": None,
        "guest": None,
        "ip": "192.168.1.12",
        "mac": "00:aa:11:bb:22:dd",
        "node": "00:aa:11:bb:22:cc",
        "online": True,
        "rssi": -34,
    }
}


@pytest.mark.parametrize(
    (
        "data_clientlist",
        "data_allclientlist",
        "result_clientlist",
        "result_allclientlist",
    ),
    [
        # Correct data
        (
            DATA_CLIENTLIST,
            DATA_ALLCLIENTLIST,
            RESULT_CLIENTLIST,
            RESULT_ALLCLIENTLIST,
        ),
        # AiMesh node data missing
        (None, DATA_ALLCLIENTLIST, None, RESULT_ALLCLIENTLIST),
        # Clients data missing
        (DATA_CLIENTLIST, None, RESULT_CLIENTLIST, None),
        # No data
        (None, None, None, None),
    ],
)
def test_process(
    data_clientlist: list[dict[str, Any]] | None,
    data_allclientlist: list[dict[str, Any]] | None,
    result_clientlist: dict[str, AiMeshDevice] | None,
    result_allclientlist: dict[str, dict[str, Any]] | None,
) -> None:
    """Test process function."""

    # Test data and expected result
    data = {}
    expected_result = {}

    # AiMesh nodes data
    if data_clientlist is not None:
        data["get_cfg_clientlist"] = data_clientlist
    expected_result[AsusData.AIMESH] = result_clientlist or {}

    # Clients data
    if data_allclientlist is not None:
        data["get_allclientlist"] = data_allclientlist
    expected_result[AsusData.CLIENTS] = result_allclientlist or {}

    # Define the side effects for the mocked functions
    def mock_aimesh_node_side_effect(
        device: dict[str, Any],
    ) -> AiMeshDevice | None:
        """Mock the process_aimesh_node function."""

        if result_clientlist and device.get("mac") in result_clientlist:
            return result_clientlist[device.get("mac")]
        return None

    # Patch the functions and set their return values
    with (
        patch(
            "asusrouter.modules.endpoint.onboarding.process_aimesh_node",
            side_effect=mock_aimesh_node_side_effect,
        ) as mock_aimesh_node,
        patch(
            "asusrouter.modules.endpoint.onboarding.process_connection",
            return_value=result_allclientlist,
        ) as mock_connection,
    ):
        # Get the result
        result = process(data)

        # Assert that the result is as expected
        assert result == expected_result

        # Check that mock_aimesh_node was called
        # (if data_clientlist was provided)
        if data_clientlist is not None:
            assert len(mock_aimesh_node.call_args_list) == len(
                data_clientlist[0]
            )
            for i, call in enumerate(mock_aimesh_node.call_args_list):
                assert call.args[0] == data_clientlist[0][i]
        else:
            mock_aimesh_node.assert_not_called()

        # Check that mock_connection was called appropriate number of times
        if data_allclientlist is not None:
            assert mock_connection.call_count == len(data_allclientlist)
        else:
            mock_connection.assert_not_called()


def test_process_aimesh_node() -> None:
    """Test process_aimesh_node function."""

    # Test data and expected result
    data = {
        "ap2g": "ap2g_value",
        "ap5g": "ap5g_value",
        "ap5g1": "ap5g1_value",
        "ap6g": "ap6g_value",
        "apdwb": "apdwb_value",
        "pap2g": "",
        "pap5g": "pap5g_value",
        "pap6g": "pap6g_value",
        "rssi2g": "",
        "rssi5g": "rssi5g_value",
        "rssi6g": "rssi6g_value",
        "pap2g_ssid": "",
        "pap5g_ssid": "pap5g_ssid_value",
        "pap6g_ssid": "pap6g_ssid_value",
        "level": "1",
        "online": "1",
        "alias": "alias_value",
        "ui_model_name": "ui_model_name_value",
        "model_name": "model_name_value",
        "product_id": "product_id_value",
        "ip": "192.168.0.2",
        "fwver": "fwver_value",
        "newfwver": "newfwver_value",
        "mac": "00:aa:11:bb:22:cc",
        "config": {"config_key": "config_value"},
    }
    expected_result = AiMeshDevice(
        status=True,
        alias="alias_value",
        model="ui_model_name_value",
        product_id="product_id_value",
        ip="192.168.0.2",
        fw="fwver_value",
        fw_new="newfwver_value",
        mac="00:aa:11:bb:22:cc",
        ap={
            "2ghz": "ap2g_value",
            "5ghz": "ap5g_value",
            "5ghz2": "ap5g1_value",
            "6ghz": "ap6g_value",
            "dwb": "apdwb_value",
        },
        parent={
            "connection": "5ghz",
            "mac": "pap5g_value",
            "rssi": "rssi5g_value",
            "ssid": "pap5g_ssid_value",
        },
        type="node",
        level=1,
        config={"config_key": "config_value"},
    )

    # Get the result
    result = process_aimesh_node(data)

    # Check the result
    assert result == expected_result


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        # An empty string
        ("", {}),
        # Data for a wired connection
        ("wired_mac", {"connection_type": 0, "guest": 0}),
        # Data for a wireless guest connection
        (
            "type_1",
            {"connection_type": CONNECTION_TYPE.get("type") or 0, "guest": 1},
        ),
        # Wrong data
        (None, {}),
        (123, {}),
    ],
)
def test_process_connection(
    data: str | None, expected: dict[str, int]
) -> None:
    """Test process_connection function."""

    result = process_connection(data)
    assert result == expected
