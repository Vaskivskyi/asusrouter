"""Library init"""

from .error import (
    AsusRouterError,
    AsusRouterConnectionError,
    AsusRouterConnectionTimeoutError,
    AsusRouterServerDisconnectedError,
    AsusRouterLoginError,
    AsusRouterLoginBlockError,
    AsusRouterResponseError,
    AsusRouterServiceError,
    AsusRouterValueError,
    AsusRouterSSLError,
    AsusRouterIdentityError,
)

from .connection import (
    Connection as Connection,
)

from .asusrouter import (
    AsusRouter as AsusRouter,
)

from .dataclass import (
    ConnectedDevice,
    Key,
    Monitor,
)