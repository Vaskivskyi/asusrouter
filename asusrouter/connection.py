"""Connection module"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import urllib.parse
from typing import Any

import aiohttp

from asusrouter import (
    AsusRouter404,
    AsusRouterAuthorizationError,
    AsusRouterConnectionError,
    AsusRouterConnectionTimeoutError,
    AsusRouterError,
    AsusRouterLoginBlockError,
    AsusRouterLoginError,
    AsusRouterResponseError,
    AsusRouterServerDisconnectedError,
    AsusRouterSSLError,
)
from asusrouter.const import (
    AR_API,
    AR_ERROR_CODE,
    AR_USER_AGENT,
    AUTHORIZATION,
    CREDENTIALS,
    DEFAULT_PORT,
    DEFAULT_SLEEP_CONNECTING,
    DEFAULT_SLEEP_RECONNECT,
    ENDPOINT,
    ENDPOINT_LOGIN,
    ENDPOINT_LOGOUT,
    ERROR_STATUS,
    HOOK,
    HTTP,
    HTTPS,
    LOGOUT,
    SUCCESS,
    TRY_AGAIN,
)
from asusrouter.util import converters, parsers

_LOGGER = logging.getLogger(__name__)


class Connection:
    """Create connection"""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int | None = None,
        use_ssl: bool = False,
        session: aiohttp.ClientSession | None = None,
    ):
        """Properties for connection"""

        self._host: str | None = host
        self._port: int | None = port
        self._username: str | None = username
        self._password: str | None = password
        self._token: str | None = None
        self._headers: dict[str, str] | None = None
        self._session: aiohttp.ClientSession | None = session

        self._device: dict[str, str] = {}
        self._error: bool = False
        self._connecting: bool = False
        self._mute_flag: bool = False
        self._drop: bool = False

        self._http = HTTPS if use_ssl else HTTP
        self._ssl = False

        if self._port is None or self._port == 0:
            self._port = DEFAULT_PORT[self._http]

        self._connected: bool = None

    async def async_run_command(
        self, command: str, endpoint: str = ENDPOINT[HOOK], retry: bool = False
    ) -> dict[str, Any]:
        """Run command. Use the existing connection token, otherwise create new one"""

        if self._drop:
            return {}

        if self._token is None and not retry:
            _LOGGER.debug("No token - connecting and repeating")
            await self.async_connect()
            return await self.async_run_command(command, endpoint, retry=True)
        if self._token is not None:
            try:
                result = await self.async_request(command, endpoint, self._headers)
                return result
            except AsusRouterAuthorizationError as ex:
                if not retry:
                    await self.async_connect()
                    return await self.async_run_command(command, endpoint, retry=True)
                raise ex
            except AsusRouterError as ex:
                raise ex
            except Exception as ex:
                if not retry:
                    await self.async_connect()
                    return await self.async_run_command(command, endpoint, retry=True)
                raise ex
        else:
            _LOGGER.error("Error sending a command to `%s`", endpoint)
            return {}

    async def async_load(self, endpoint: str, retry: bool = False) -> str:
        """Load the page"""

        if self._drop:
            return {}

        if self._token is None and not retry:
            await self.async_connect()
            return await self.async_load(endpoint, retry=True)

        string_body = str()

        try:
            async with self._session.post(
                url=f"{self._http}://{self._host}:{self._port}/{endpoint}",
                headers=self._headers,
                ssl=self._ssl,
            ) as reply:
                string_body = await reply.text()
                if "404 Not Found" in string_body:
                    raise AsusRouter404()
        except (aiohttp.ClientError, asyncio.TimeoutError) as ex:
            if not retry:
                return self.async_load(endpoint, retry=True)
            raise AsusRouterConnectionError(ex) from ex
        except Exception as ex:
            raise ex

        return string_body

    async def async_request(
        self, payload: str, endpoint: str, headers: dict[str, str], retry: bool = False
    ) -> dict[str, Any]:
        """Send a request"""

        if self._drop:
            return {}

        # Wait a bit before just retrying
        if retry:
            await asyncio.sleep(DEFAULT_SLEEP_RECONNECT)

        # Connection process
        if endpoint == ENDPOINT_LOGIN:
            self._connecting = True
        # Sleep if we got here during the connection process
        else:
            while self._connecting:
                await asyncio.sleep(DEFAULT_SLEEP_CONNECTING)

        json_body = {}

        try:
            async with self._session.post(
                url=f"{self._http}://{self._host}:{self._port}/{endpoint}",
                data=urllib.parse.quote(payload),
                headers=headers,
                ssl=self._ssl,
            ) as reply:
                string_body = await reply.text()
                if string_body == str():
                    return {}
                if "404 Not Found" in string_body:
                    raise AsusRouter404()
                json_body = await reply.json()

                # Handle reported errors
                if ERROR_STATUS in json_body:
                    # If got here, we are not connected properly
                    self._connected = False

                    # ERROR CODES
                    error_code = int(json_body[ERROR_STATUS])
                    # Not authorized
                    if error_code == AR_ERROR_CODE[AUTHORIZATION]:
                        raise AsusRouterAuthorizationError("Session is not authorized")
                    # Wrong crerdentials
                    if error_code == AR_ERROR_CODE[CREDENTIALS]:
                        raise AsusRouterLoginError("Wrong credentials")
                    # Too many attempts
                    if error_code == AR_ERROR_CODE[TRY_AGAIN]:
                        raise AsusRouterLoginBlockError(
                            "Too many attempts to login",
                            timeout=converters.int_from_str(
                                json_body["remaining_lock_time"]
                            ),
                        )
                    # Loged out
                    if error_code == AR_ERROR_CODE[LOGOUT]:
                        return {SUCCESS: True}
                    # Unknown error code
                    raise AsusRouterResponseError(
                        f"Unknown error code `{error_code}`, please report it"
                    )

            # If loged in, save the device API data
            if endpoint == ENDPOINT_LOGIN:
                r_headers = reply.headers
                for item in AR_API:
                    if item in r_headers:
                        self._device[item] = r_headers[item]

            # Reset mute_flag on success
            self._mute_flag = False

            return json_body

        # Handle non-JSON replies
        except json.JSONDecodeError:
            if ".xml" in endpoint:
                json_body = parsers.xml(text=string_body)
            else:
                json_body = parsers.pseudo_json(text=string_body, page=endpoint)
            return json_body

        # Raise only if mute_flag not set
        except aiohttp.ClientSSLError as ex:
            if not self._mute_flag:
                raise AsusRouterSSLError() from ex
        except (aiohttp.ServerTimeoutError, asyncio.TimeoutError) as ex:
            if not self._mute_flag:
                raise AsusRouterConnectionTimeoutError() from ex
        # This happens regularly if more connections are established.
        # Repeat before actually raising the exception
        except aiohttp.ServerDisconnectedError as ex:
            if retry:
                raise AsusRouterServerDisconnectedError(ex) from ex
            _LOGGER.debug(
                "Disconnected by the device while quering '%s' with payload '%s'. "
                "Everything should recover by itself. If this warning appears regularly, "
                "you might need to decrease the number of simultaneous connections "
                "to your device",
                endpoint,
                payload,
            )

        # Connection refused or reset by peer -> will repeat
        except (aiohttp.ClientOSError) as ex:
            if endpoint == ENDPOINT_LOGIN and not self._mute_flag:
                raise AsusRouterConnectionError(str(ex)) from ex
            # Mute warning for retries and while connecting
            if not retry and not self._connecting:
                _LOGGER.debug(
                    "Connection refused. Endpoint: %s. Payload: %s.\nException summary: %s",
                    endpoint,
                    payload,
                    str(ex),
                )

        # If it got here, something is wrong. Reconnect and retry
        self._mute_flag = True

        if not retry:
            self._error = True
            _LOGGER.debug("Reconnecting")
            await self.async_cleanup()
            await self.async_connect(retry=True)
        return await self.async_request(
            payload=payload, endpoint=endpoint, headers=headers, retry=True
        )

    async def async_connect(self, retry: bool = False) -> bool:
        """Start new connection to and get new auth token"""

        _LOGGER.debug("Trying to connect")

        _success = False
        self._drop = False

        if self._session is None:
            _LOGGER.debug("No client session provided. Starting a new session")
            self._session = aiohttp.ClientSession()

        auth = f"{self._username}:{self._password}".encode("ascii")
        logintoken = base64.b64encode(auth).decode("ascii")
        payload = f"login_authorization={logintoken}"
        headers = {"user-agent": AR_USER_AGENT}

        _LOGGER.debug("Sending connection request")
        response = await self.async_request(
            payload=payload, endpoint=ENDPOINT_LOGIN, headers=headers, retry=retry
        )
        if "asus_token" in response:
            self._token = response["asus_token"]
            self._headers = {
                "user-agent": AR_USER_AGENT,
                "cookie": f"asus_token={self._token}",
            }
            _LOGGER.debug("Login successful on port `%s`: %s", self._port, self._device)

            self._connected = True
            _success = True
        else:
            _LOGGER.error("Cannot recieve a token from device")

        self._connecting = False

        return _success

    async def async_disconnect(self) -> bool:
        """Close the connection"""

        # Not connected
        if not self._connected:
            _LOGGER.debug("Not connected")
        # Connected
        else:
            try:
                result = await self.async_request("", ENDPOINT_LOGOUT, self._headers)
                if SUCCESS not in result:
                    return False
            except AsusRouterAuthorizationError:
                _LOGGER.debug("Connection was already droped")

        # Clean up
        await self.async_cleanup()

        return True

    async def async_drop_connection(self) -> None:
        """Drop connection"""

        self._drop = True
        await self.async_cleanup()

    async def async_cleanup(self) -> None:
        """Cleanup after logout"""

        _LOGGER.debug("Cleaning up")

        self._connected = False
        self._token = None
        self._headers = None

    async def async_reset_error(self) -> None:
        """Reset error flag"""

        self._error = False
        return

    @property
    def connected(self) -> bool:
        """Connection status"""

        return self._connected

    @property
    def connecting(self) -> bool:
        """Connection progress"""

        return self._connecting

    @property
    def device(self) -> dict[str, str]:
        """Device model and API support levels"""

        return self._device

    @property
    def error(self) -> bool:
        """Report errors"""

        return self._error
