"""Error module."""

from __future__ import annotations

from typing import Any

import aiohttp


class AsusRouterError(Exception):
    """Base class for errors in AsusRouter library."""

    def __init__(
        self, *args: Any, message: str | None = None, **_kwargs: Any
    ) -> None:
        """Initialise base error."""

        super().__init__(*args, message)


class AsusRouterRequestFormatError(AsusRouterError):
    """Request format error."""


class AsusRouterConnectionError(
    AsusRouterError, aiohttp.ClientConnectionError
):
    """Connection error."""


class AsusRouterTimeoutError(AsusRouterError):
    """Timeout error."""


class AsusRouterSSLCertificateError(AsusRouterError):
    """SSL certificate error."""


class AsusRouter404Error(AsusRouterError):
    """Page not found error."""


class AsusRouterAccessError(AsusRouterError):
    """Access error."""


class AsusRouterLogoutError(AsusRouterError):
    """Logout error."""


class AsusRouterFallbackError(AsusRouterError):
    """Fallback error."""


class AsusRouterFallbackForbiddenError(AsusRouterFallbackError):
    """Fallback forbidden error."""


class AsusRouterFallbackLoopError(AsusRouterFallbackError):
    """Fallback loop error."""
