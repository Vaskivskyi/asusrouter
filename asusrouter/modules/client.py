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
            if item is not None and item != str():
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
