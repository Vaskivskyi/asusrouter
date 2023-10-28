"""Constants module for AsusRouter"""

from enum import Enum


# Enums
class ContentType(str, Enum):
    """Content type enum."""

    JSON = "application/json"
    TEXT = "text/plain"
    HTML = "text/html"


# Asus constants
USER_AGENT = "asusrouter--DUTUtil-"

# Library defaults
DEFAULT_CACHE_TIME = 5.0
DEFAULT_SLEEP_TIME = 0.1
DEFAULT_TIMEOUT = 10.0
DEFAULT_TIMEOUT_CONNECTION = 180.0

DEFAULT_TIMEOUTS = [
    5.0,
    10.0,
    20.0,
    30.0,
    60.0,
    120.0,
    180.0,
]

# --------------------
# Value maps -->
# --------------------
# These maps are used to read data from the device
# into the correct variables and apply a converter if needed


# --------------------
# <-- Value maps
# --------------------
