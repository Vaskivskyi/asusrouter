"""Test AsusRouter connection tools."""

import aiohttp

import pytest
from asusrouter.tools.connection import get_cookie_jar


@pytest.mark.asyncio
async def test_get_cookie_jar() -> None:
    """Test get_cookie_jar method."""

    jar = get_cookie_jar()
    assert isinstance(jar, aiohttp.CookieJar)
    assert jar._unsafe is True
    assert jar._quote_cookie is False
