"""Error module"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

import aiohttp


class AsusRouterError(Exception):
    """Base class for errors in AsusRouter library"""

    def __init__(
        self, *args: Any, message: Optional[str] = None, **_kwargs: Any
    ) -> None:
        """Initialise base error"""

        super().__init__(*args, message)


class AsusRouterConnectionError(AsusRouterError, aiohttp.ClientConnectionError):
    """Error connecting to the router"""


class AsusRouterConnectionTimeoutError(
    AsusRouterError, aiohttp.ServerTimeoutError, asyncio.TimeoutError
):
    """Timeout error on communication"""


class AsusRouterServerDisconnectedError(
    AsusRouterError, aiohttp.ServerDisconnectedError
):
    """Server disconnected error"""


class AsusRouterSSLError(
    AsusRouterError,
    aiohttp.ClientConnectorSSLError,
    aiohttp.ClientConnectorCertificateError,
):
    """SSL error"""


class AsusRouterLoginError(AsusRouterError):
    """Login error / credentials error"""


class AsusRouterLoginBlockError(AsusRouterError):
    """Too many attempts error on device side"""

    def __init__(
        self,
        *args: Any,
        message: Optional[str] = None,
        timeout: Optional[int] = None,
        **_kwargs: Any,
    ) -> None:
        """Initialise base error"""

        self._timeout = timeout

        super().__init__(*args, message)

    @property
    def timeout(self) -> int | None:
        """Return timeout"""

        return self._timeout


class AsusRouterResponseError(AsusRouterError, aiohttp.ClientResponseError):
    """Error on communication"""


class AsusRouterServiceError(AsusRouterError):
    """Error on calling a service"""


class AsusRouterValueError(AsusRouterError, ValueError):
    """Invalid value received"""


class AsusRouterNotImplementedError(AsusRouterError, NotImplementedError):
    """Not implemented error"""


class AsusRouterIdentityError(AsusRouterError):
    """Error of collecting device identity"""


class AsusRouter404(AsusRouterError):
    """Error on page not found"""
