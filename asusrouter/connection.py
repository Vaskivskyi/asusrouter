"""Connection module"""

from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)

import asyncio
import base64
import json
import ssl
import urllib.parse
from pathlib import Path
from typing import Any

import aiohttp

from asusrouter import (
    AsusRouter404,
    AsusRouterConnectionError,
    AsusRouterConnectionTimeoutError,
    AsusRouterLoginBlockError,
    AsusRouterLoginError,
    AsusRouterResponseError,
    AsusRouterServerDisconnectedError,
    AsusRouterSSLError,
)
from asusrouter.const import (
    AR_API,
    AR_ERROR,
    AR_PATH,
    AR_USER_AGENT,
    DEFAULT_PORT,
    DEFAULT_SLEEP_CONNECTING,
    DEFAULT_SLEEP_RECONNECT,
    MSG_ERROR,
    MSG_INFO,
    MSG_SUCCESS,
    MSG_WARNING,
)
from asusrouter.util import converters, parsers


class Connection:
    """Create connection"""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int | None = None,
        use_ssl: bool = False,
        cert_check: bool = True,
        cert_path: str = "",
    ):
        """Properties for connection"""

        self._host: str | None = host
        self._port: int | None = port
        self._username: str | None = username
        self._password: str | None = password
        self._token: str | None = None
        self._headers: dict[str, str] | None = None
        self._session: aiohttp.ClientSession | None = None

        self._device: dict[str, str] = dict()
        self._error: bool = False
        self._connecting: bool = False
        self._mute_flag: bool = False
        self._drop: bool = False

        self._http = "https" if use_ssl else "http"

        if self._port is None or self._port == 0:
            self._port = DEFAULT_PORT[self._http]

        if cert_check:
            if cert_path != "":
                path = Path(cert_path)
                if path.is_file():
                    self._ssl = ssl.create_default_context(cafile=cert_path)
                    _LOGGER.debug(MSG_SUCCESS["cert_found"])
                else:
                    _LOGGER.error(MSG_ERROR["cert_missing"])
                    self._ssl = True
            else:
                _LOGGER.debug(MSG_INFO["no_cert"])
                self._ssl = True
        else:
            _LOGGER.debug(MSG_INFO["no_cert_check"])
            self._ssl = False

        self._connected: bool = None

    async def async_run_command(
        self, command: str, endpoint: str = AR_PATH["get"], retry: bool = False
    ) -> dict[str, Any]:
        """Run command. Use the existing connection token, otherwise create new one"""

        if self._drop:
            return {}

        if self._token is None and not retry:
            await self.async_connect()
            return await self.async_run_command(command, endpoint, retry=True)
        else:
            if self._token is not None:
                try:
                    result = await self.async_request(command, endpoint, self._headers)
                    return result
                except (AsusRouter404, AsusRouterServerDisconnectedError) as ex:
                    raise ex
                except Exception as ex:
                    if not retry:
                        await self.async_connect()
                        return await self.async_run_command(
                            command, endpoint, retry=True
                        )
                    else:
                        _LOGGER.error(
                            MSG_ERROR["command"].format(command, endpoint, ex)
                        )
                        return {}
            else:
                _LOGGER.error(MSG_ERROR["command"].format(command, endpoint))
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
                url="{}://{}:{}/{}".format(
                    self._http, self._host, self._port, endpoint
                ),
                headers=self._headers,
                ssl=self._ssl,
            ) as r:
                string_body = await r.text()
                if "404 Not Found" in string_body:
                    raise AsusRouter404()
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
        if endpoint == AR_PATH["login"]:
            self._connecting = True
        # Sleep if we got here during the connection process
        else:
            while self._connecting:
                await asyncio.sleep(DEFAULT_SLEEP_CONNECTING)

        json_body = {}

        try:
            async with self._session.post(
                url="{}://{}:{}/{}".format(
                    self._http, self._host, self._port, endpoint
                ),
                data=urllib.parse.quote(payload),
                headers=headers,
                ssl=self._ssl,
            ) as r:
                string_body = await r.text()
                if "404 Not Found" in string_body:
                    raise AsusRouter404()
                json_body = await r.json()

                # Handle reported errors
                if "error_status" in json_body:
                    # If got here, we are not connected properly
                    self._connected = False

                    ## ERROR CODES
                    error_code = int(json_body["error_status"])
                    # Not authorised
                    if error_code == AR_ERROR["authorisation"]:
                        raise AsusRouterResponseError(MSG_ERROR["authorisation"])
                    # Wrong crerdentials
                    elif error_code == AR_ERROR["credentials"]:
                        raise AsusRouterLoginError(MSG_ERROR["credentials"])
                    # Too many attempts
                    elif error_code == AR_ERROR["try_again"]:
                        _LOGGER.debug(json_body)
                        raise AsusRouterLoginBlockError(
                            MSG_ERROR["try_again"],
                            timeout=converters.int_from_str(
                                json_body["remaining_lock_time"]
                            ),
                        )
                    # Loged out
                    elif error_code == AR_ERROR["logout"]:
                        _LOGGER.info(MSG_SUCCESS["logout"])
                        return {"success": True}
                    # Unknown error code
                    else:
                        raise AsusRouterResponseError(
                            MSG_ERROR["unknown"].format(error_code)
                        )

            # If loged in, save the device API data
            if endpoint == AR_PATH["login"]:
                r_headers = r.headers
                for item in AR_API:
                    if item in r_headers:
                        self._device[item] = r_headers[item]

            # RReset mute_flag on success
            self._mute_flag = False

            return json_body

        # Handle non-JSON replies
        except json.JSONDecodeError:
            if ".xml" in endpoint:
                _LOGGER.debug(MSG_INFO["xml"])
                json_body = parsers.xml(text=string_body, page=endpoint)
            else:
                _LOGGER.debug(MSG_INFO["json_fix"])
                json_body = parsers.pseudo_json(text=string_body, page=endpoint)
            return json_body

        # Raise only if mute_flag not set
        except (
            aiohttp.ClientConnectorSSLError,
            aiohttp.ClientConnectorCertificateError,
        ) as ex:
            if not self._mute_flag:
                raise AsusRouterSSLError()
        except (aiohttp.ServerTimeoutError, asyncio.TimeoutError) as ex:
            if not self._mute_flag:
                raise AsusRouterConnectionTimeoutError()
        except aiohttp.ServerDisconnectedError as ex:
            if not self._mute_flag:
                raise AsusRouterServerDisconnectedError()

        # Connection refused -> will repeat
        except aiohttp.ClientConnectorError as ex:
            if endpoint == AR_PATH["login"] and not self._mute_flag:
                raise AsusRouterConnectionError(str(ex)) from ex
            # Mute warning for retries and while connecting
            if not retry and not self._connecting:
                _LOGGER.warning(
                    "{}. Endpoint: {}. Payload: {}.\nException summary:{}".format(
                        MSG_WARNING["refused"], endpoint, payload, str(ex)
                    )
                )

        # If it got here, something is wrong. Reconnect and retry
        self._mute_flag = True

        if not retry:
            self._error = True
            _LOGGER.info(MSG_INFO["reconnect"])
            await self.async_cleanup()
            await self.async_connect(retry=True)
        return await self.async_request(
            payload=payload, endpoint=endpoint, headers=headers, retry=True
        )

    async def async_connect(self, retry: bool = False) -> bool:
        """Start new connection to and get new auth token"""

        _success = False
        self._drop = False

        if self._session is None:
            self._session = aiohttp.ClientSession()

        auth = "{}:{}".format(self._username, self._password).encode("ascii")
        logintoken = base64.b64encode(auth).decode("ascii")
        payload = "login_authorization={}".format(logintoken)
        headers = {"user-agent": AR_USER_AGENT}

        response = await self.async_request(
            payload=payload, endpoint=AR_PATH["login"], headers=headers, retry=retry
        )
        if "asus_token" in response:
            self._token = response["asus_token"]
            self._headers = {
                "user-agent": AR_USER_AGENT,
                "cookie": "asus_token={}".format(self._token),
            }
            _LOGGER.info(
                "{} on port {}: {}".format(
                    MSG_SUCCESS["login"], self._port, self._device
                )
            )

            self._connected = True
            _success = True
        else:
            _LOGGER.error(MSG_ERROR["token"])

        self._connecting = False

        return _success

    async def async_disconnect(self) -> bool:
        """Close the connection"""

        # Not connected
        if not self._connected:
            _LOGGER.debug(MSG_WARNING["not_connected"])
        # Connected
        else:
            result = await self.async_request("", AR_PATH["logout"], self._headers)
            if not "success" in result:
                return False

        # Clean up
        await self.async_cleanup()

        return True

    async def async_drop_connection(self) -> None:
        """Drop connection"""

        self._drop = True
        await self.async_cleanup()

    async def async_cleanup(self) -> None:
        """Cleanup after logout"""

        self._connected = False
        self._token = None
        self._headers = None
        if self._session is not None:
            await self._session.close()
        self._session = None

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
