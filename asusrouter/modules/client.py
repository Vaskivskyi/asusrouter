"""Client module for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from asusrouter.modules.connection import (
    ConnectionState,
    ConnectionType,
    InternetMode,
    get_connection_type,
    get_internet_mode,
)
from asusrouter.modules.const import MapValueType
from asusrouter.modules.ip_address import IPAddressType, read_ip_address_type
from asusrouter.modules.vendor import replace_vendor
from asusrouter.tools.converters import (
    safe_bool,
    safe_float,
    safe_int,
    safe_time_from_delta,
    safe_unpack_key,
)


@dataclass
class AsusClient:
    """Client class."""

    state: ConnectionState = ConnectionState.UNKNOWN

    description: Optional[AsusClientDescription] = None

    connection: Optional[AsusClientConnection] = None


@dataclass
class AsusClientConnection:
    """Connection class."""

    type: ConnectionType = ConnectionType.DISCONNECTED
    ip_address: Optional[str] = None
    ip_method: Optional[str] = None
    internet_state: Optional[bool] = None
    internet_mode: InternetMode = InternetMode.UNKNOWN
    node: Optional[str] = None
    online: bool = False

    # Is an AiMesh node
    aimesh: Optional[bool] = None


@dataclass
class AsusClientConnectionWlan(AsusClientConnection):
    """WLAN connection class."""

    guest: Optional[bool] = None
    guest_id: Optional[int] = None
    rssi: Optional[int] = None
    since: Optional[datetime] = None
    rx_speed: Optional[float] = None
    tx_speed: Optional[float] = None


@dataclass
class AsusClientDescription:
    """Client description class."""

    name: Optional[str] = None
    mac: Optional[str] = None

    vendor: Optional[str] = None


CLIENT_MAP: dict[str, list[MapValueType]] = {
    "connected_since": [
        ("wlConnectTime", safe_time_from_delta),
    ],
    "connection_type": [
        ("connection_type"),
        ("isWL", safe_int),
    ],
    "guest": [
        ("guest"),
        ("isGN", safe_int),
    ],
    "internet_mode": [
        ("internetMode", get_internet_mode),
    ],
    "internet_state": [
        ("internetState", safe_bool),
    ],
    "ip": [
        ("ip"),
    ],
    "ip_method": [
        ("ipMethod"),
    ],
    "mac": [
        ("mac"),
    ],
    "name": [
        ("nickName"),
        ("name"),
        ("mac"),
    ],
    "node": [
        ("node"),
    ],
    "online": [
        ("online"),
        ("isOnline", safe_bool),
    ],
    "rssi": [
        ("rssi", safe_int),
    ],
    "rx_speed": [
        ("curRx", safe_float),
    ],
    "tx_speed": [
        ("curTx", safe_float),
    ],
}

CLIENT_MAP_DESCRIPTION: dict[str, list[MapValueType]] = {
    "name": [
        ("nickName"),
        ("name"),
        ("mac"),
    ],
    "mac": [
        ("mac"),
    ],
    "vendor": [
        ("vendor", replace_vendor),
    ],
}

CLIENT_MAP_CONNECTION: dict[str, list[MapValueType]] = {
    "type": [
        ("connection_type", get_connection_type),
        ("isWL", get_connection_type),
    ],
    "ip_address": [
        ("ip"),
    ],
    "ip_method": [
        ("ipMethod", read_ip_address_type),
    ],
    "internet_state": [
        ("internetState", safe_bool),
    ],
    "internet_mode": [
        ("internetMode", get_internet_mode),
    ],
    "node": [
        ("node"),
    ],
    "online": [
        ("online", safe_bool),
        ("isOnline", safe_bool),
    ],
    "aimesh": [
        ("amesh_isRe", safe_bool),
    ],
}

CLIENT_MAP_CONNECTION_WLAN: dict[str, list[MapValueType]] = {
    "guest_id": [
        ("guest"),
        ("isGN", safe_int),
    ],
    "rssi": [
        ("rssi", safe_int),
    ],
    "since": [
        ("wlConnectTime", safe_time_from_delta),
    ],
    "rx_speed": [
        ("curRx", safe_float),
    ],
    "tx_speed": [
        ("curTx", safe_float),
    ],
}


def process_client(
    data: dict[str, Any], history: Optional[AsusClient] = None, **kwargs: Any
) -> AsusClient:
    """
    Process client data.

    Parameters:
    data (dict[str, Any]): The client data to process.
    history (Optional[AsusClient]): The previous state of the client, if any.

    Returns:
    AsusClient: The processed client data.
    """

    description: AsusClientDescription = process_client_description(data)
    connection: AsusClientConnection | AsusClientConnectionWlan = (
        process_client_connection(data)
    )

    state: ConnectionState = process_client_state(connection, **kwargs)

    # Clean disconnected client
    if state != ConnectionState.CONNECTED:
        connection = process_disconnected(connection)

    # Check history for the oscillating values
    if history is not None and history.connection is not None:
        connection = process_history(connection, history.connection)

    return AsusClient(state=state, description=description, connection=connection)


def process_data(data: dict[str, Any], mapping: dict[str, Any], obj: Any) -> Any:
    """Process data based on a mapping and set attributes on an object."""

    # Go through all keys in mapping
    for key, value in mapping.items():
        for pair in value:
            # Get the search key and converter(s)
            key_to_find, converters = safe_unpack_key(pair)
            # Get the value from the data
            item = data.get(key_to_find)

            # Process the value if it's an actual value
            if item is not None and item != str():
                # Apply converters one by one if there are multiple
                if isinstance(converters, list):
                    for converter in converters:
                        item = converter(item)
                # Apply single converter
                elif converters:
                    item = converters(item)

                # Set the attribute on the object
                setattr(obj, key, item)

                # We found the value, no need to continue searching
                break

    return obj


def process_client_description(data: dict[str, Any]) -> AsusClientDescription:
    """Process client description data."""

    return process_data(data, CLIENT_MAP_DESCRIPTION, AsusClientDescription())


def process_client_connection(data: dict[str, Any]) -> AsusClientConnection:
    """Process client connection data."""

    connection = process_data(data, CLIENT_MAP_CONNECTION, AsusClientConnection())

    if not connection.type in (ConnectionType.WIRED, ConnectionType.DISCONNECTED):
        connection = process_client_connection_wlan(data, connection)

    return connection


def process_client_connection_wlan(
    data: dict[str, Any], base_connection: AsusClientConnection
) -> AsusClientConnectionWlan:
    """Process WLAN client connection data."""

    wlan_connection = AsusClientConnectionWlan(**base_connection.__dict__)
    wlan_connection = process_data(data, CLIENT_MAP_CONNECTION_WLAN, wlan_connection)

    # Mark `guest` attribute if `guest_id` is non-zero
    wlan_connection.guest = (
        wlan_connection.guest_id != 0 and wlan_connection.guest_id is not None
    )

    return wlan_connection


def process_client_state(
    connection: AsusClientConnection,
    **kwargs: Any,
) -> ConnectionState:
    """Process client state."""

    # If no IP address or type is disconnected, it's disconnected
    if connection.ip_address is None or connection.type == ConnectionType.DISCONNECTED:
        return ConnectionState.DISCONNECTED

    # If client is an AiMesh node, it's not a client
    if connection.aimesh is True:
        return ConnectionState.DISCONNECTED

    # If we have support for AiMesh but no node, client is disconnected
    aimesh = kwargs.get("aimesh", False)
    if aimesh is True and connection.node is None:
        return ConnectionState.DISCONNECTED

    # This one is a weak check, should always be the last one
    if connection.online is True:
        return ConnectionState.CONNECTED

    return ConnectionState.DISCONNECTED


def process_disconnected(connection: AsusClientConnection) -> AsusClientConnection:
    """Process disconnected client."""

    # We keep values set by the user:
    # - internet mode
    # - ip method
    # - ip address if ip method is static
    return AsusClientConnection(
        type=ConnectionType.DISCONNECTED,
        ip_address=connection.ip_address
        if connection.ip_method == IPAddressType.STATIC
        else None,
        ip_method=connection.ip_method,
        internet_mode=connection.internet_mode,
    )


def process_history(
    connection: AsusClientConnection, history: AsusClientConnection
) -> AsusClientConnection:
    """Process values from history to avoid oscillating values."""

    # Wireless connection
    if isinstance(connection, AsusClientConnectionWlan) and isinstance(
        history, AsusClientConnectionWlan
    ):
        # Fix the oscillating connection time ignore any value less than 10 seconds
        # This comes from the device itself and cannot be fixed from AsusRouter side
        if connection.since is not None and history.since is not None:
            diff = abs((history.since - connection.since).total_seconds())
            if diff < 10:
                connection.since = history.since

    return connection
