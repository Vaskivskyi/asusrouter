"""Connection tools for AsusRouter."""

from __future__ import annotations

import aiohttp


def get_cookie_jar() -> aiohttp.CookieJar:
    """Get a cookie jar for the AsusRouter connection."""

    return aiohttp.CookieJar(unsafe=True, quote_cookie=False)
