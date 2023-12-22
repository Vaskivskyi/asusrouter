"""Tests for the client module."""

from datetime import datetime, timezone
from unittest import mock

import pytest

from asusrouter.modules.client import (
    CLIENT_MAP_CONNECTION,
    CLIENT_MAP_CONNECTION_WLAN,
    CLIENT_MAP_DESCRIPTION,
    AsusClient,
    AsusClientConnection,
    AsusClientConnectionWlan,
    AsusClientDescription,
    process_client,
    process_client_connection,
    process_client_connection_wlan,
    process_client_description,
    process_client_state,
    process_data,
    process_disconnected,
    process_history,
)
from asusrouter.modules.connection import ConnectionState, ConnectionType, InternetMode
from asusrouter.modules.ip_address import IPAddressType


@pytest.mark.parametrize(
    "state, history, process_disconnected_calls, process_history_calls",
    [
        (ConnectionState.CONNECTED, None, 0, 0),
        (ConnectionState.DISCONNECTED, None, 1, 0),
        (ConnectionState.DISCONNECTED, AsusClient(), 1, 0),
        (
            ConnectionState.DISCONNECTED,
            AsusClient(connection=AsusClientConnection()),
            1,
            1,
        ),
    ],
)
@mock.patch("asusrouter.modules.client.process_history")
@mock.patch("asusrouter.modules.client.process_disconnected")
@mock.patch("asusrouter.modules.client.process_client_state")
@mock.patch("asusrouter.modules.client.process_client_connection")
@mock.patch("asusrouter.modules.client.process_client_description")
def test_process_client(
    process_client_description_mock,
    process_client_connection_mock,
    process_client_state_mock,
    process_disconnected_mock,
    process_history_mock,
    state,
    history,
    process_disconnected_calls,
    process_history_calls,
):
    """Test process_client."""

    # Prepare input data
    data = {"key": "value"}

    # Mock function return values
    process_client_description_mock.return_value = AsusClientDescription()
    process_client_connection_mock.return_value = AsusClientConnection()
    process_client_state_mock.return_value = state
    process_disconnected_mock.return_value = AsusClientConnection()
    process_history_mock.return_value = AsusClientConnection()

    # Get the result
    result = process_client(data, history)

    # Check the result
    assert isinstance(result, AsusClient)
    assert result.description == process_client_description_mock.return_value
    assert result.connection == process_history_mock.return_value
    assert result.state == process_client_state_mock.return_value

    # Check that the mocked functions were called the correct number of times
    process_client_description_mock.assert_called_once_with(data)
    process_client_connection_mock.assert_called_once_with(data)
    process_client_state_mock.assert_called_once_with(
        process_client_connection_mock.return_value
    )
    assert process_disconnected_mock.call_count == process_disconnected_calls
    assert process_history_mock.call_count == process_history_calls


@pytest.mark.parametrize(
    "data, mapping, expected_attribute_values, obj_type",
    [
        # AsusClientDescription
        (
            {
                "name_key": "Client1",
                "mac_key": "00:11:22:33:44:55",
                "vendor_key": "Vendor1",
            },
            {
                "name": [("name_key", str)],
                "mac": [("mac_key", str)],
                "vendor": [("vendor_key", str)],
            },
            {
                "name": "Client1",
                "mac": "00:11:22:33:44:55",
                "vendor": "Vendor1",
            },
            AsusClientDescription,
        ),
        # AsusClientConnection
        (
            {
                "connection_type": ConnectionType.WLAN_2G,
                "ip": "192.168.1.2",
                "internetState": "1",
            },
            {
                "type": [("connection_type", None)],
                "ip_address": [("ip", str)],
                "internet_state": [("internetState", int)],
            },
            {
                "type": ConnectionType.WLAN_2G,
                "ip_address": "192.168.1.2",
                "internet_state": 1,
            },
            AsusClientConnection,
        ),
        # AsusClientConnectionWlan
        (
            {
                "guest_id_key": "1",
                "rssi_key": "-50",
            },
            {
                "guest_id": [("guest_id_key", int)],
                "guest": [("guest_id_key", [int, bool])],
                "rssi": [("rssi_key", int)],
            },
            {
                "guest_id": 1,
                "guest": True,
                "rssi": -50,
            },
            AsusClientConnectionWlan,
        ),
    ],
)
@mock.patch("asusrouter.modules.client.safe_unpack_key", side_effect=lambda pair: pair)
def test_process_data(
    safe_unpack_key_mock, data, mapping, expected_attribute_values, obj_type
):
    """Test process_data."""

    # Get the result
    result = process_data(data, mapping, obj_type())

    # Check the result
    assert isinstance(result, obj_type)

    # Check that safe_unpack_key_mock was called the correct number of times
    assert safe_unpack_key_mock.call_count == len(mapping)

    # Check that the result has the correct attributes and they were correctly converted
    for key in mapping:
        assert hasattr(result, key)
        assert getattr(result, key) == expected_attribute_values[key]


@mock.patch("asusrouter.modules.client.process_data")
def test_process_client_description(process_data_mock):
    """Test process_client_description."""

    # Prepare input data
    data = {
        "name_key": "Client1",
        "mac_key": "00:11:22:33:44:55",
        "vendor_key": "Vendor1",
    }

    # Call the function
    process_client_description(data)

    # Check that process_data was called with the correct arguments
    process_data_mock.assert_called_once_with(
        data, CLIENT_MAP_DESCRIPTION, AsusClientDescription()
    )


@pytest.mark.parametrize(
    "connection_type, process_wlan_calls",
    [
        (ConnectionType.WIRED, 0),
        (ConnectionType.WLAN_2G, 1),
    ],
)
@mock.patch(
    "asusrouter.modules.client.process_data",
    side_effect=lambda data, mapping, obj: AsusClientConnection(
        type=data.get("connection_type")
    ),
)
@mock.patch("asusrouter.modules.client.process_client_connection_wlan")
def test_process_client_connection(
    process_client_connection_wlan_mock,
    process_data_mock,
    connection_type,
    process_wlan_calls,
):
    """Test process_client_connection."""

    # Prepare input data
    data = {
        "connection_type": connection_type,
        "ip": "192.168.1.2",
        "internetState": "1",
    }

    # Call the function
    process_client_connection(data)

    # Check that process_data was called with the correct arguments
    process_data_mock.assert_called_once_with(
        data, CLIENT_MAP_CONNECTION, AsusClientConnection()
    )

    # Check that process_client_connection_wlan was called the correct number of times
    assert process_client_connection_wlan_mock.call_count == process_wlan_calls


@mock.patch(
    "asusrouter.modules.client.process_data", return_value=AsusClientConnectionWlan()
)
def test_process_client_connection_wlan(process_data_mock):
    """Test process_client_connection_wlan."""

    # Prepare input data
    data = {
        "guest_id_key": "1",
        "rssi_key": "50",
    }
    connection = AsusClientConnection()

    # Call the function
    result = process_client_connection_wlan(data, connection)

    # Check that process_data was called with the correct arguments
    process_data_mock.assert_called_once_with(
        data,
        CLIENT_MAP_CONNECTION_WLAN,
        AsusClientConnectionWlan(**connection.__dict__),
    )

    # Check the result
    assert isinstance(result, AsusClientConnectionWlan)


@pytest.mark.parametrize(
    "ip_address, connection_type, aimesh, node, online, expected_result",
    [
        # No IP address
        (
            None,
            ConnectionType.WLAN_2G,
            False,
            None,
            False,
            ConnectionState.DISCONNECTED,
        ),
        # Connection type is disconnected
        (
            "192.168.1.11",
            ConnectionType.DISCONNECTED,
            False,
            None,
            False,
            ConnectionState.DISCONNECTED,
        ),
        # Client is an AiMesh node
        (
            "192.168.1.11",
            ConnectionType.WLAN_2G,
            True,
            None,
            False,
            ConnectionState.DISCONNECTED,
        ),
        # No node assigned, offline
        (
            "192.168.1.11",
            ConnectionType.WLAN_2G,
            False,
            None,
            False,
            ConnectionState.DISCONNECTED,
        ),
        # No node assigned, online
        (
            "192.168.1.11",
            ConnectionType.WLAN_2G,
            False,
            None,
            True,
            ConnectionState.CONNECTED,
        ),
        # Node assigned, offline
        (
            "192.168.1.11",
            ConnectionType.WLAN_2G,
            False,
            "00:AA:BB:CC:00:01",
            False,
            ConnectionState.CONNECTED,
        ),
        # Node assigned, online
        (
            "192.168.1.11",
            ConnectionType.WLAN_2G,
            False,
            "00:AA:BB:CC:00:01",
            True,
            ConnectionState.CONNECTED,
        ),
    ],
)
def test_process_client_state(
    ip_address, connection_type, aimesh, node, online, expected_result
):
    """Test process_client_state."""

    # Prepare input data
    connection = AsusClientConnection(
        type=connection_type,
        ip_address=ip_address,
        aimesh=aimesh,
        node=node,
        online=online,
    )

    # Check the result
    assert process_client_state(connection) == expected_result


@pytest.mark.parametrize(
    "connection_type, ip_method, ip_address, internet_mode, expected_ip_address",
    [
        (
            ConnectionType.WLAN_2G,
            IPAddressType.DHCP,
            "192.168.1.2",
            InternetMode.ALLOW,
            None,
        ),
        (
            ConnectionType.WLAN_5G,
            IPAddressType.STATIC,
            "192.168.1.2",
            InternetMode.BLOCK,
            "192.168.1.2",
        ),
    ],
)
def test_process_disconnected(
    connection_type,
    ip_method,
    ip_address,
    internet_mode,
    expected_ip_address,
):
    """Test process_disconnected."""

    # Prepare input data
    connection = AsusClientConnection(
        type=connection_type,
        ip_method=ip_method,
        ip_address=ip_address,
        internet_mode=internet_mode,
    )

    # Get the result
    result = process_disconnected(connection)

    # Check the result
    assert isinstance(result, AsusClientConnection)
    assert result.type == ConnectionType.DISCONNECTED
    assert result.ip_address == expected_ip_address
    assert result.ip_method == ip_method
    assert result.internet_mode == internet_mode


@pytest.mark.parametrize(
    "connection_class, history_class, connection_since, histore_since, expected_result",
    [
        # Valid WLAN connection
        # Time difference is less than 10 seconds
        (AsusClientConnectionWlan, AsusClientConnectionWlan, 9, 0, "history"),
        (AsusClientConnectionWlan, AsusClientConnectionWlan, 0, 1, "history"),
        # Time difference is more than 10 seconds
        (AsusClientConnectionWlan, AsusClientConnectionWlan, 10, 0, "connection"),
        (AsusClientConnectionWlan, AsusClientConnectionWlan, 0, 11, "connection"),
        # No time provided
        (AsusClientConnectionWlan, AsusClientConnectionWlan, None, 0, "connection"),
        (AsusClientConnectionWlan, AsusClientConnectionWlan, 0, None, "connection"),
        # Not WLAN connection,
        (AsusClientConnection, AsusClientConnectionWlan, 10, 0, "connection"),
        (AsusClientConnectionWlan, AsusClientConnection, 10, 0, "connection"),
        (AsusClientConnection, AsusClientConnection, 10, 0, "connection"),
    ],
)
def test_process_history(
    connection_class, history_class, connection_since, histore_since, expected_result
):
    """Test process_history."""

    # Prepare input data
    data = {
        "connection": connection_class(),
        "history": history_class(),
    }

    if (
        isinstance(data["connection"], AsusClientConnectionWlan)
        and connection_since is not None
    ):
        data["connection"].since = datetime(
            2023, 11, 9, 10, 15, connection_since, tzinfo=timezone.utc
        )

    if (
        isinstance(data["history"], AsusClientConnectionWlan)
        and histore_since is not None
    ):
        data["history"].since = datetime(
            2023, 11, 9, 10, 15, histore_since, tzinfo=timezone.utc
        )

    # Get the result
    result = process_history(data["connection"], data["history"])

    # Check the result
    assert result == data[expected_result]
