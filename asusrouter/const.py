"""Constants module for AsusRouter."""

from enum import IntEnum, StrEnum
from typing import Final

from asusrouter.tools.enum import FromIntMixin

# Version information
MAJOR_VERSION: Final[int] = 2
MINOR_VERSION: Final[int] = 0
PATCH_VERSION: Final[str] = "0.dev0"
__version__: Final[str] = f"{MAJOR_VERSION}.{MINOR_VERSION}.{PATCH_VERSION}"


# Unknown member constants
UNKNOWN_MEMBER: Final[int] = -999
UNKNOWN_MEMBER_STR: Final[str] = "unknown"


# Enums
class ContentType(StrEnum):
    """Content type enum."""

    UNKNOWN = "unknown"

    BINARY = "application/octet-stream"
    HTML = "text/html"
    JSON = "application/json"
    TEXT = "text/plain"
    XML = "application/xml"


class RequestType(StrEnum):
    """Request type enum."""

    GET = "get"
    POST = "post"


class HTTPStatus(FromIntMixin, IntEnum):
    """HTTP status codes."""

    UNKNOWN = UNKNOWN_MEMBER

    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    INTERNAL_SERVER_ERROR = 500
    JSON_BAD_FORMAT = 4002
    JSON_BAD_REQUEST = 4003


# Asus constants
USER_AGENT = f"asusrouter-library-DUTUtil-{__version__}"
DEFAULT_PORT_HTTP = 80
DEFAULT_PORT_HTTPS = 8443

# AsusRouter definitions
AR_CALL_GET_STATE = "get_state"
AR_CALL_SET_STATE = "set_state"
AR_CALL_TRANSLATE_STATE = "translate_state"

# Library defaults
DEFAULT_CACHE_TIME = 5.0
DEFAULT_SLEEP_TIME = 0.1
DEFAULT_TIMEOUT = 15
DEFAULT_TIMEOUT_FALLBACK = 5

DEFAULT_RESULT_SUCCESS = {"statusCode": "200"}

# --------------------
# Value maps -->
# --------------------
# These maps are used to read data from the device
# into the correct variables and apply a converter if needed


# --------------------
# <-- Value maps
# --------------------
