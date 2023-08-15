"""Connection module"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.parse
from typing import Any, Optional, Union

import aiohttp

from asusrouter import (
    AsusRouter404,
    AsusRouterAuthorizationError,
    AsusRouterConnectionError,
    AsusRouterConnectionTimeoutError,
    AsusRouterError,
    AsusRouterSSLError,
)
from asusrouter.const import (
    AR_API,
    AR_USER_AGENT,
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
    SUCCESS,
)
from asusrouter.util import communication

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

    async def _handle_exception(
        self,
        ex: Exception,
        command: str,
        endpoint: str,
        retry: bool,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Handle exceptions"""

        match ex:
            case AsusRouterAuthorizationError():
                if not retry:
                    await self.async_connect()
                    return await self.async_run_command(command, endpoint, retry=True)
                raise ex
            case AsusRouterConnectionError():
                if not retry:
                    return await self.async_load(endpoint, retry=True)
                raise ex
            case AsusRouterError():
                raise ex
            case json.JSONDecodeError():
                string_body = kwargs.get("string_body")
                return communication.handle_json_decode_error(string_body, endpoint)
            case aiohttp.ClientSSLError():
                await self._handle_client_ssl_error(ex)
            case aiohttp.ServerTimeoutError():
                await self._handle_server_timeout_error(ex)
            case aiohttp.ServerDisconnectedError():
                communication.handle_server_disconnected_error(
                    ex, endpoint, command, retry
                )
            case aiohttp.ClientOSError():
                await self._handle_client_os_error(ex, endpoint, command, retry)
            case Exception():
                raise ex

        _LOGGER.error("Error sending a command to `%s`", endpoint)
        return {}

    async def _check_token_and_connect(self):
        """Check if there is a valid token and attempt to connect if necessary"""

        if self._token is None:
            _LOGGER.debug("No token - connecting and repeating")
            await self.async_connect()

    async def _make_post_request(
        self,
        endpoint: str,
        payload: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> Union[str, dict[str, Any]]:
        """Make a POST request to the given endpoint with the given payload and headers"""

        if headers is None:
            headers = self._headers

        string_body: str = str()
        reply_headers: dict[str, Any] = []

        try:
            async with self._session.post(
                url=f"{self._http}://{self._host}:{self._port}/{endpoint}",
                data=urllib.parse.quote(payload) if payload is not None else None,
                headers=headers,
                ssl=self._ssl,
            ) as reply:
                string_body = await reply.text()
                reply_headers = reply.headers
                if "404 Not Found" in string_body:
                    raise AsusRouter404()
                if payload is not None:
                    json_body = await reply.json()

                    # Handle reported errors
                    if json_body is not None and ERROR_STATUS in json_body:
                        # If got here, we are not connected properly
                        self._connected = False

                        # Handle error codes
                        communication.handle_error_codes(json_body)

                    return json_body, reply_headers
        except Exception as ex:
            result =  await self._handle_exception(
                ex, "", endpoint, False, string_body=string_body
            )
            if isinstance(result, dict):
                return result, reply_headers

        return string_body, reply_headers

    async def async_run_command(
        self, command: str, endpoint: str = ENDPOINT[HOOK], retry: bool = False
    ) -> dict[str, Any]:
        """Run command. Use the existing connection token, otherwise create new one"""

        if self._drop:
            return {}

        await self._check_token_and_connect()

        try:
            result = await self.async_request(command, endpoint, self._headers)
            return result
        except Exception as ex:
            return await self._handle_exception(ex, command, endpoint, retry)

    async def async_load(self, endpoint: str, retry: bool = False) -> str:
        """Load the page"""

        if self._drop:
            return {}

        if not retry:
            await self._check_token_and_connect()

        string_body = str()

        try:
            string_body, _headers = await self._make_post_request(endpoint=endpoint)
        except Exception as ex:
            return await self._handle_exception(ex, "", endpoint, retry)

        return string_body

    async def _handle_client_ssl_error(self, ex: aiohttp.ClientSSLError) -> None:
        """Handle a ClientSSLError"""

        if not self._mute_flag:
            raise AsusRouterSSLError() from ex

    async def _handle_server_timeout_error(
        self, ex: aiohttp.ServerTimeoutError
    ) -> None:
        """Handle a ServerTimeoutError"""

        if not self._mute_flag:
            raise AsusRouterConnectionTimeoutError() from ex

    async def _handle_client_os_error(
        self, ex: aiohttp.ClientOSError, endpoint: str, payload: str, retry: bool
    ) -> None:
        """Handle a ClientOSError"""

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

    async def _save_device_api_data(self, headers: dict[str, str]) -> None:
        """Save the device API data from the given headers"""

        self._device = {item: headers[item] for item in AR_API if item in headers}

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

        try:
            json_body, headers = await self._make_post_request(
                endpoint=endpoint, payload=payload, headers=headers
            )

            # If loged in, save the device API data
            if endpoint == ENDPOINT_LOGIN:
                await self._save_device_api_data(headers)

            # Reset mute_flag on success
            self._mute_flag = False

            return json_body

        except Exception as ex:
            return await self._handle_exception(ex, payload, endpoint, retry)

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

    async def _create_session_if_needed(self) -> None:
        """Create a new session if one does not already exist"""

        if self._session is None:
            _LOGGER.debug("No client session provided. Starting a new session")
            self._session = aiohttp.ClientSession()

    async def async_connect(self, retry: bool = False) -> bool:
        """Start new connection to and get new auth token"""

        _LOGGER.debug("Trying to connect")

        _success = False
        self._drop = False

        await self._create_session_if_needed()

        payload, headers = communication.generate_credentials(
            self._username, self._password
        )

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
