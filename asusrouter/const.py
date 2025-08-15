"""Constants module for AsusRouter."""

from enum import IntEnum, StrEnum


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


class HTTPStatus(IntEnum):
    """HTTP status codes."""

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


# Asus constants
USER_AGENT = "asusrouter--DUTUtil-"
DEFAULT_PORT_HTTP = 80
DEFAULT_PORT_HTTPS = 8443

# Library defaults
DEFAULT_CACHE_TIME = 5.0
DEFAULT_SLEEP_TIME = 0.1
DEFAULT_TIMEOUT = 15
DEFAULT_TIMEOUT_FALLBACK = 5

DEFAULT_RESULT_SUCCESS = {"statusCode": "200"}

UNKNOWN_MEMBER = -999

# --------------------
# Value maps -->
# --------------------
# These maps are used to read data from the device
# into the correct variables and apply a converter if needed


# --------------------
# <-- Value maps
# --------------------
