"""Connection module."""

from enum import Enum, IntEnum
from typing import Optional

from asusrouter.modules.wlan import Wlan
from asusrouter.tools.converters import get_enum_key_by_value, safe_int


class ConnectionState(IntEnum):
    """Connection state enum."""

    UNKNOWN = -999

    DISCONNECTED = 0
    CONNECTED = 1


class ConnectionStatus(IntEnum):
    """Connection status enum."""

    UNKNOWN = -999

    ERROR = -1
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2


class ConnectionType(str, Enum):
    """Connection type class."""

    WIRED = "wired"
    WLAN_2G = Wlan.FREQ_2G.value
    WLAN_5G = Wlan.FREQ_5G.value
    WLAN_5G2 = Wlan.FREQ_5G2.value
    WLAN_6G = Wlan.FREQ_6G.value
    DISCONNECTED = "disconnected"


CONNECTION_TYPE = {
    0: ConnectionType.WIRED,
    1: ConnectionType.WLAN_2G,
    2: ConnectionType.WLAN_5G,
    3: ConnectionType.WLAN_5G2,
    4: ConnectionType.WLAN_6G,
}


class InternetMode(str, Enum):
    """Internet mode class."""

    ALLOW = "allow"
    BLOCK = "block"
    TIME = "time"
    UNKNOWN = "unknown"


def get_internet_mode(value: str) -> InternetMode:
    """Get internet mode."""

    return get_enum_key_by_value(InternetMode, value, InternetMode.UNKNOWN)


def get_connection_type(value: Optional[int]) -> ConnectionType:
    """Get connection type."""

    # Check that it's actually an int
    # This would actually work with float as well doing direct conversion
    value = safe_int(value)

    # ------------------------------------------------------ #
    # I am officially considering this a feature, not a bug. #
    # ------------------------------------------------------ #

    if value is None:
        value = 0

    return CONNECTION_TYPE.get(value, ConnectionType.WIRED)
