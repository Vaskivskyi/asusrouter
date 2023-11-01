"""Connection module.

This module handles the connection between the library and the router 
as well as all the data transfer."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Any, Optional, Tuple
from urllib.parse import quote

import aiohttp

from asusrouter.const import DEFAULT_TIMEOUTS, USER_AGENT
from asusrouter.error import (
    AsusRouter404Error,
    AsusRouterAccessError,
    AsusRouterConnectionError,
    AsusRouterError,
    AsusRouterLogoutError,
    AsusRouterSessionError,
    AsusRouterTimeoutError,
)
from asusrouter.modules.endpoint import Endpoint, EndpointControl, EndpointService
from asusrouter.modules.endpoint.error import AccessError, handle_access_error

_LOGGER = logging.getLogger(__name__)


def generate_credentials(username: str, password: str) -> Tuple[str, dict[str, str]]:
    """Generate credentials for connection"""

    auth = f"{username}:{password}".encode("ascii")
    logintoken = base64.b64encode(auth).decode("ascii")
    payload = f"login_authorization={logintoken}"
    headers = {"user-agent": "asusrouter--DUTUtil-"}

    return payload, headers


class Connection:  # pylint: disable=too-many-instance-attributes
    """A connection between the library and the device."""

    # A token for the current session
    _token: Optional[str] = None
    # A header to use in the current session
    _header: Optional[dict[str, str]] = None

    # SSL
    _ssl = False

    # Connection status
    _connected: bool = False
    _connection_lock: asyncio.Lock = asyncio.Lock()

    def __init__(  # pylint: disable=too-many-arguments
        self,
        hostname: str,
        username: str,
        password: str,
        port: Optional[int] = None,
        use_ssl: bool = False,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        """Initialize connection."""

        _LOGGER.debug("Initializing a new connection to `%s`", hostname)

        # Hostname and credentials
        self._hostname = hostname
        self._username = username
        self._password = password

        # Client session
        self._session = session if session is not None else aiohttp.ClientSession()
        _LOGGER.debug("Using session `%s`", session)

        # Set the port and protocol based on the input
        self._http = "https" if use_ssl else "http"
        self._port = port or (8443 if use_ssl else 80)
        _LOGGER.debug("Using `%s` and port `%s`", self._http, self._port)

    async def async_connect(
        self, retry: int = 0, lock: Optional[asyncio.Lock] = None
    ) -> bool:
        """Connect to the device and get a new auth token."""

        # Check that we are connected so that we don't try to go through lock again
        if self._connected:
            _LOGGER.debug("Already connected to %s", self._hostname)
            return True

        _lock = lock or self._connection_lock

        async with _lock:
            # Again check if we are connected and return if we are
            if self._connected:
                return True

            _LOGGER.debug("Initializing connection to %s", self._hostname)
            self._connected = False

            # Generate payload and header for login request
            payload, headers = generate_credentials(self._username, self._password)

            # Request authotization
            _LOGGER.debug("Requesting authorization")
            try:
                _, _, resp_content = await self._send_request(
                    EndpointService.LOGIN, payload, headers
                )
                _LOGGER.debug("Received authorization response")
            except AsusRouterAccessError as ex:
                # Check the AccessError
                if ex.args[1] == AccessError.TRY_AGAIN:
                    # Get the timeout
                    timeout = ex.args[2].get("timeout") + 5
                    if timeout:
                        _LOGGER.debug("Will try again in %s seconds", timeout)
                        await asyncio.sleep(timeout)
                        return await self.async_connect(retry, asyncio.Lock())
                    raise ex
                # In case of any other error, switch to the next except block
                raise ex
            except AsusRouterError as ex:
                _LOGGER.debug("Connection failed")
                if retry < len(DEFAULT_TIMEOUTS) - 1:
                    _LOGGER.debug(
                        "Will try again in %s seconds", DEFAULT_TIMEOUTS[retry]
                    )
                    await asyncio.sleep(DEFAULT_TIMEOUTS[retry])
                    return await self.async_connect(retry + 1, asyncio.Lock())
                raise AsusRouterTimeoutError(
                    f"Reached maximum allowed timeout\
                        for a single connection attempt: {sum(DEFAULT_TIMEOUTS)}"
                ) from ex
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.debug("Error while connecting to %s: %s", self._hostname, ex)
                raise ex

            # Convert the response to JSON
            content = json.loads(resp_content)
            # Get the auth_token value from the headers
            self._token = content.get("asus_token")
            if not self._token:
                _LOGGER.error("No token received")
                return False

            # Set the header
            self._header = {
                "user-agent": USER_AGENT,
                "cookie": f"asus_token={self._token}",
            }

            # Mark as connected
            self._connected = True
            _LOGGER.debug("Connected to %s", self._hostname)

            return True

    async def async_disconnect(self) -> bool:
        """Disconnect from the device."""

        _LOGGER.debug("Initializing disconnection from %s", self._hostname)

        # Check that we are connected
        if not self._connected:
            _LOGGER.debug("Not connected to %s", self._hostname)
            return True

        # Request logout
        try:
            await self._send_request(EndpointService.LOGOUT)
        except AsusRouterLogoutError:
            # Loged out successfully
            self.reset_connection()
            _LOGGER.debug("Disconnected from %s", self._hostname)
            return True
        except AsusRouterError as ex:
            _LOGGER.debug("Error while disconnecting from %s: %s", self._hostname, ex)
            return False

        # Anything else would mean error when disconnecting
        return False

    async def _send_request(
        self,
        endpoint: Endpoint | EndpointControl | EndpointService,
        payload: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> Tuple[int, dict[str, str], str]:
        """Send a request to the device."""

        # Send request
        try:
            resp_status, resp_headers, resp_content = await self._make_post_request(
                endpoint,
                payload,
                headers,
            )

            # Raise exception on 404
            if resp_status == 404:
                raise AsusRouter404Error(f"Endpoint {endpoint} not found")

            # Raise exception on non-200 status
            if resp_status != 200:
                raise AsusRouterAccessError(
                    f"Cannot access {endpoint}, status {resp_status}"
                )

            # Check for access errors
            if "error_status" in resp_content:
                return handle_access_error(
                    endpoint, resp_status, resp_headers, resp_content
                )

            return (resp_status, resp_headers, resp_content)
        except aiohttp.ClientConnectorError as ex:
            self.reset_connection()
            raise AsusRouterConnectionError from ex
        except (aiohttp.ClientConnectionError, aiohttp.ClientOSError) as ex:
            raise AsusRouterConnectionError from ex
        except Exception as ex:  # pylint: disable=broad-except
            raise ex

    async def async_query(
        self,
        endpoint: Endpoint | EndpointControl | EndpointService,
        payload: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> Tuple[int, dict[str, str], str]:
        """Send a request to the device."""

        # If not connected, try to connect
        if not self._connected:
            _LOGGER.debug("Not connected to %s. Connecting...", self._hostname)
            await self.async_connect()

        # If still not connected, raise an error
        if not self._connected:
            raise AsusRouterTimeoutError("Data cannot be retrieved. Connection failed")

        # Send the request
        _LOGGER.debug("Sending request to %s", self._hostname)
        return await self._send_request(endpoint, payload, headers)

    async def _make_post_request(
        self,
        endpoint: Endpoint | EndpointControl | EndpointService,
        payload: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> Any:
        """Make a post request to the device."""

        # Check if a session is available
        if self._session is None:
            # If no session is available, we cannot be connected to the device
            # So we don't try to make any requests
            raise AsusRouterSessionError("No session available for this connection")

        # Check headers
        if not headers:
            headers = self._header

        # Generate the url
        url = f"{self._http}://{self._hostname}:{self._port}/{endpoint.value}"

        # Process the payload to be sent
        payload_to_send = quote(payload) if payload else None

        # Send the request
        async with self._session.post(
            url,
            data=payload_to_send,
            headers=headers,
            ssl=self._ssl,
        ) as response:
            # Read the status code
            resp_status = response.status

            # Read the response headers
            resp_headers = response.headers

            # Read the response
            try:
                resp_content = await response.text()
            except UnicodeDecodeError:
                _LOGGER.debug("Cannot decode response. Will ignore errors")
                resp_content = await response.text(errors="ignore")

            # Return the response
            return (resp_status, resp_headers, resp_content)

    def reset_connection(self):
        """Reset connection variables."""

        if not self._connected:
            return

        _LOGGER.debug("Resetting connection to %s", self._hostname)

        self._connected = False
        self._token = None
        self._header = None

    @property
    def connected(self) -> bool:
        """Return connection status."""

        return self._connected
