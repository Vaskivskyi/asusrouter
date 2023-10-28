"""Error module."""

from __future__ import annotations

from typing import Any, Optional

import aiohttp


class AsusRouterError(Exception):
    """Base class for errors in AsusRouter library."""

    def __init__(
        self, *args: Any, message: Optional[str] = None, **_kwargs: Any
    ) -> None:
        """Initialise base error."""

        super().__init__(*args, message)


class AsusRouterDataError(AsusRouterError):
    """Any error with received data."""


class AsusRouterConnectionError(AsusRouterError, aiohttp.ClientConnectionError):
    """Connection error."""


class AsusRouterTimeoutError(AsusRouterError):
    """Timeout error."""


class AsusRouterSessionError(AsusRouterError):
    """Session error."""


class AsusRouter404Error(AsusRouterError):
    """Page not found error."""


class AsusRouterIdentityError(AsusRouterError):
    """Identity error."""


class AsusRouterAccessError(AsusRouterError):
    """Access error."""


class AsusRouterLogoutError(AsusRouterError):
    """Logout error."""


class AsusRouterServiceError(AsusRouterError):
    """Service error."""
