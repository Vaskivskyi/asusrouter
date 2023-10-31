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
from asusrouter.modules.ip_address import IPAddressType, read_ip_address_type
from asusrouter.modules.vendor import replace_vendor
from asusrouter.tools.converters import (
    safe_bool,
    safe_float,
    safe_int,
    safe_time_from_delta,
    safe_unpack_key,
)

# # Map of the parameters for connected device
# # value_to_find: [where_to_search, method to convert]
# # List is sorted by importance with the most important first
# MAP_CONNECTED_DEVICE: dict[str, list[SearchKey]] = {
#     "connected_since": [
#         SearchKey("wlConnectTime", time_from_delta),
#     ],
#     CONNECTION_TYPE: [
#         SearchKey(CONNECTION_TYPE),
#         SearchKey("isWL", int_from_str),
#     ],
#     GUEST: [
#         SearchKey(GUEST),
#         SearchKey("isGN", int_from_str),
#     ],
#     "internet_mode": [
#         SearchKey("internetMode"),
#     ],
#     "internet_state": [
#         SearchKey("internetState", bool_from_any),
#     ],
#     IP: [
#         SearchKey(IP),
#     ],
#     "ip_method": [
#         SearchKey("ipMethod"),
#     ],
#     MAC: [
#         SearchKey(MAC),
#     ],
#     NAME: [
#         SearchKey("nickName"),
#         SearchKey(NAME),
#         SearchKey(MAC),
#     ],
#     NODE: [
#         SearchKey(NODE),
#     ],
#     ONLINE: [
#         SearchKey(ONLINE),
#         SearchKey("isOnline", bool_from_any),
#     ],
#     RSSI: [
#         SearchKey(RSSI, int_from_str),
#     ],
#     "rx_speed": [
#         SearchKey("curRx", float_from_str),
#     ],
#     "tx_speed": [
#         SearchKey("curTx", float_from_str),
#     ],
# }


# List of available attributes for a device:
#
# "amesh_bind_band": "0",
# "amesh_bind_mac": "",
# "amesh_isRe": "0",
# "amesh_isReClient": "1",
# "amesh_papMac": "7C:10:C9:03:6D:90",
# "callback": "",
# "curRx": "        ",
# "curTx": "1",
# "defaultType": "0",
# "dpiDevice": "",
# "dpiType": "",
# "group": "",
# "internetMode": "block",
# "internetState": 0,
# "ip": "192.168.55.112",
# "ipMethod": "Manual",
# "isGN": "",
# "isGateway": "0",
# "isITunes": "0",
# "isLogin": "0",
# "isOnline": "1",
# "isPrinter": "0",
# "isWL": "1",
# "isWebServer": "0",
# "keeparp": "",
# "mac": "E0:98:06:C4:25:92",
# "macRepeat": "0",
# "name": "Espressif Inc ",
# "nickName": "Fr/Socket/Bookshelf",
# "opMode": "0",
# "os_type": 0,
# "qosLevel": "",
# "ROG": "0",
# "rssi": "-55",
# "ssid": "",
# "totalRx": "",
# "totalTx": "",
# "type": "0",
# "vendor": "Espressif Inc.",
# "vendorclass": "Espressif Inc.",
# "wtfast": "0",
# "wlConnectTime": "00:00:03"


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


CLIENT_MAP = {
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

CLIENT_MAP_DESCRIPTION = {
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

CLIENT_MAP_CONNECTION = {
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
}

CLIENT_MAP_CONNECTION_WLAN = {
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
    data: dict[str, Any], history: Optional[AsusClient] = None
) -> AsusClient:
    """Process client data."""

    description = process_client_description(data)
    connection = process_client_connection(data)

    state = process_client_state(connection)

    # Clean disconnected client
    if state != ConnectionState.CONNECTED:
        connection = process_disconnected(connection)

    # Check history for the oscillating values
    if history is not None and history.connection is not None:
        connection = process_history(connection, history.connection)

    return AsusClient(state=state, description=description, connection=connection)


def process_client_description(data: dict[str, Any]) -> AsusClientDescription:
    """Process client description data."""

    description = AsusClientDescription()

    for key, value in CLIENT_MAP_DESCRIPTION.items():
        for pair in value:
            key_to_find, converter = safe_unpack_key(pair)
            item = data.get(key_to_find)
            if item and item != str():
                setattr(
                    description,
                    key,
                    converter(item) if converter else item,
                )
                break

    return description


def process_client_connection(data: dict[str, Any]) -> AsusClientConnection:
    """Process client connection data."""

    connection = AsusClientConnection()

    for key, value in CLIENT_MAP_CONNECTION.items():
        for pair in value:
            key_to_find, converter = safe_unpack_key(pair)
            item = data.get(key_to_find)
            if item and item != str():
                setattr(
                    connection,
                    key,
                    converter(item) if converter else item,
                )
                break

    if not connection.type in (ConnectionType.WIRED, ConnectionType.DISCONNECTED):
        connection = process_client_connection_wlan(data, connection)

    return connection


def process_client_connection_wlan(
    data: dict[str, Any], connection: AsusClientConnection
) -> AsusClientConnectionWlan:
    """Process WLAN client connection data."""

    connection = AsusClientConnectionWlan(**connection.__dict__)

    for key, value in CLIENT_MAP_CONNECTION_WLAN.items():
        for pair in value:
            key_to_find, converter = safe_unpack_key(pair)
            item = data.get(key_to_find)
            if item and item != str():
                setattr(
                    connection,
                    key,
                    converter(item) if converter else item,
                )
                break

    # Mark `guest` attribute if `guest_id` is non-zero
    connection.guest = connection.guest_id != 0 and connection.guest_id is not None

    return connection


def process_client_state(
    connection: AsusClientConnection,
) -> ConnectionState:
    """Process client state."""

    # If client has node attribute, it's connected
    if connection.node is not None:
        return ConnectionState.CONNECTED

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
