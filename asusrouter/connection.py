"""Connection module.

This module handles the connection between the library and the router
as well as all the data transfer."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Any, Awaitable, Callable, Optional, Tuple
from urllib.parse import quote

import aiohttp

from asusrouter.const import DEFAULT_TIMEOUT, USER_AGENT, RequestType
from asusrouter.error import (
    AsusRouter404Error,
    AsusRouterAccessError,
    AsusRouterConnectionError,
    AsusRouterError,
    AsusRouterLogoutError,
    AsusRouterTimeoutError,
)
from asusrouter.modules.endpoint import EndpointService, EndpointType
from asusrouter.modules.endpoint.error import handle_access_error

_LOGGER = logging.getLogger(__name__)

PAYLOAD_TO_CLEAN = [
    "login_authorization",
]


def clean_payload(payload: Optional[str]) -> Optional[str]:
    """Clean the payload for logging"""

    if not payload:
        return payload

    # If any of the payload keys are in the list, replace the whole
    # payload with `REDACTED`
    for key in PAYLOAD_TO_CLEAN:
        if key in payload:
            return "REDACTED"

    return payload


def generate_credentials(
    username: str, password: str
) -> Tuple[str, dict[str, str]]:
    """Generate credentials for connection"""

    auth = f"{username}:{password}".encode("ascii")
    logintoken = base64.b64encode(auth).decode("ascii")
    payload = f"login_authorization={logintoken}"
    headers = {"user-agent": USER_AGENT}

    return payload, headers


class Connection:  # pylint: disable=too-many-instance-attributes
    """A connection between the library and the device."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        hostname: str,
        username: str,
        password: str,
        port: Optional[int] = None,
        use_ssl: bool = False,
        session: Optional[aiohttp.ClientSession] = None,
        timeout: int = DEFAULT_TIMEOUT,
        dumpback: Optional[Callable[..., Awaitable[None]]] = None,
    ):
        """Initialize connection."""

        _LOGGER.debug("Initializing a new connection to `%s`", hostname)

        # Initialize parameters for connection
        self._token: Optional[str] = None
        self._header: Optional[dict[str, str]] = None
        self._connected: bool = False
        self._connection_lock: asyncio.Lock = asyncio.Lock()
        self._timeout: int = timeout

        # Hostname and credentials
        self._hostname = hostname
        self._username = username
        self._password = password

        # Set the port and protocol based on the input
        self._http = "https" if use_ssl else "http"
        self._port = port or (8443 if use_ssl else 80)
        self._ssl = use_ssl
        self._verify_ssl = False
        _LOGGER.debug(
            "Using `%s` and port `%s` with ssl flag `%s`",
            self._http,
            self._port,
            self._ssl,
        )

        # Callback for dumping data
        self._dumpback = dumpback

        # Client session
        self._manage_session: bool = False
        if session is not None:
            _LOGGER.debug("Using provided session")
            self._session = session
        else:
            _LOGGER.debug("No session provided. Will create a new one")
            self._session = self._new_session()

    async def __aenter__(self) -> Connection:
        """Enter the connection."""

        await self.async_connect()
        return self

    async def __aexit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        """Exit the connection."""

        await self.async_close()

    @classmethod
    async def create(
        cls,
        hostname: str,
        username: str,
        password: str,
        port: Optional[int] = None,
        use_ssl: bool = False,
        session: Optional[aiohttp.ClientSession] = None,
        timeout: int = DEFAULT_TIMEOUT,
        dumpback: Optional[Callable[..., Awaitable[None]]] = None,
    ) -> Connection:
        """Factory method to create and initialize a connection."""
        connection = cls(
            hostname=hostname,
            username=username,
            password=password,
            port=port,
            use_ssl=use_ssl,
            session=session,
            timeout=timeout,
            dumpback=dumpback,
        )
        await connection.async_connect()
        return connection

    def _new_session(self) -> aiohttp.ClientSession:
        """Create a new session."""

        # If we create a new session, we will manage it
        self._manage_session = True

        # Timeout for the session
        timeout = aiohttp.ClientTimeout(total=self._timeout)

        # Create the session
        return aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=self._verify_ssl),
            timeout=timeout,
        )

    async def async_close(self) -> None:
        """Close the session."""

        if self._manage_session and self._session:
            if not self._session.closed:
                _LOGGER.debug("Closing the session")
                await self._session.close()
            else:
                _LOGGER.debug("Session already closed")
        else:
            _LOGGER.debug("No session to close or not managing the session")

    async def async_connect(self, lock: Optional[asyncio.Lock] = None) -> bool:
        """Connect to the device and get a new auth token."""

        try:
            await asyncio.wait_for(
                self._async_connect_with_lock(lock), timeout=self._timeout
            )
            return True
        except asyncio.TimeoutError:
            _LOGGER.error("Connection to %s timed out", self._hostname)
            return False

    async def _async_connect_with_lock(
        self,
        lock: Optional[asyncio.Lock] = None,
    ) -> bool:
        """Connect to the device and get a new auth token."""

        # Check that we are connected
        # so that we don't try to go through lock again
        if self._connected:
            _LOGGER.debug("Already connected to %s", self._hostname)
            return True

        _lock = lock or self._connection_lock

        async with _lock:
            _LOGGER.debug("Initializing connection to %s", self._hostname)
            self._connected = False

            # Generate payload and header for login request
            payload, headers = generate_credentials(
                self._username, self._password
            )

            # Request authotization
            _LOGGER.debug("Requesting authorization")
            try:
                _, _, resp_content = await self._send_request(
                    EndpointService.LOGIN, payload, headers
                )
                _LOGGER.debug("Received authorization response")
            except AsusRouterAccessError as ex:
                raise AsusRouterAccessError(
                    f"Cannot access {EndpointService.LOGIN}. "
                    "Failed in `async_connect`"
                ) from ex
            except AsusRouterError as ex:
                _LOGGER.debug("Connection failed with error: %s", ex)
                raise
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.debug(
                    "Unexpected error while connecting to %s: %s",
                    self._hostname,
                    ex,
                )
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
            _LOGGER.debug(
                "Error while disconnecting from %s: %s", self._hostname, ex
            )
            return False

        # Anything else would mean error when disconnecting
        return False

    async def _send_request(
        self,
        endpoint: EndpointType,
        payload: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        request_type: RequestType = RequestType.POST,
    ) -> Tuple[int, dict[str, str], str]:
        """Send a request to the device."""

        # Send request
        try:
            resp_status, resp_headers, resp_content = await self._make_request(
                endpoint,
                payload,
                headers,
                request_type,
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
                handle_access_error(
                    endpoint, resp_status, resp_headers, resp_content
                )

            # Return the response
            return (resp_status, resp_headers, resp_content)
        except aiohttp.ClientConnectorError as ex:
            self.reset_connection()
            raise AsusRouterConnectionError(
                f"Cannot connect to `{self._hostname}` on port "
                f"`{self._port}`. Failed in `_send_request` with error: `{ex}`"
            ) from ex
        except (aiohttp.ClientConnectionError, aiohttp.ClientOSError) as ex:
            raise AsusRouterConnectionError(
                f"Cannot connect to `{self._hostname}` on port "
                f"`{self._port}`. Failed in `_send_request` with error: `{ex}`"
            ) from ex
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.debug(
                "Unexpected error sending request to %s with payload %s: %s",
                endpoint,
                clean_payload(payload),
                ex,
            )
            raise ex

    async def async_query(
        self,
        endpoint: EndpointType,
        payload: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        request_type: RequestType = RequestType.POST,
    ) -> Tuple[int, dict[str, str], str]:
        """Send a request to the device."""

        # If not connected, try to connect
        if not self._connected:
            _LOGGER.debug("Not connected to %s. Connecting...", self._hostname)
            await self.async_connect()

        # If still not connected, raise an error
        if not self._connected:
            raise AsusRouterTimeoutError(
                "Data cannot be retrieved. Connection failed"
            )

        # Send the request
        _LOGGER.debug(
            "Sending `%s` request to `%s`", request_type, self._hostname
        )
        return await self._send_request(
            endpoint, payload, headers, request_type
        )

    async def _make_request(
        self,
        endpoint: EndpointType,
        payload: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        request_type: RequestType = RequestType.POST,
    ) -> Any:
        """Make a post request to the device."""

        # Check if a session is available
        if self._session is None or self._session.closed:
            # If no session is available, we cannot be connected to the device
            _LOGGER.debug("No session available. Creating a new one")
            # We will create a new session and retry the request
            self.reset_connection()
            self._session = self._new_session()
            # Reconnect
            await self.async_connect()
            # Retry the request
            return await self._make_request(
                endpoint, payload, headers, request_type
            )

        # Check headers
        if not headers:
            headers = self._header

        # Generate the url
        url = f"{self._http}://{self._hostname}:{self._port}/{endpoint.value}"

        # Add get parameters if needed
        if request_type == RequestType.GET and payload:
            payload.replace(";", "&")
            url = f"{url}?{payload}"

        # Process the payload to be sent
        payload_to_send = quote(payload) if payload else None

        # Send the request
        async with self._session.request(
            request_type.value,
            url,
            data=payload_to_send if request_type == RequestType.POST else None,
            headers=headers,
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

            # Call the dumpback if available
            if self._dumpback is not None:
                await self._dumpback(
                    endpoint, payload, resp_status, resp_headers, resp_content
                )

            # Return the response
            return (resp_status, resp_headers, resp_content)

    def reset_connection(self) -> None:
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
