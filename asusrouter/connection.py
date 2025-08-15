"""Connection module.

This module handles the connection between the library and the router
as well as all the data transfer.
"""

from __future__ import annotations

import asyncio
import base64
from collections.abc import Awaitable, Callable
from enum import StrEnum
import json
import logging
import ssl
from typing import Any, Self, TypeVar
from urllib.parse import quote

import aiohttp

from asusrouter.config import ARConfig, ARConfigKey, safe_int_config
from asusrouter.connection_config import (
    ARConnectionConfig,
    ARConnectionConfigKey as ARCCKey,
)
from asusrouter.const import (
    DEFAULT_PORT_HTTP,
    DEFAULT_PORT_HTTPS,
    DEFAULT_TIMEOUT,
    USER_AGENT,
    HTTPStatus,
    RequestType,
)
from asusrouter.error import (
    AsusRouter404Error,
    AsusRouterAccessError,
    AsusRouterConnectionError,
    AsusRouterError,
    AsusRouterFallbackError,
    AsusRouterFallbackForbiddenError,
    AsusRouterFallbackLoopError,
    AsusRouterLogoutError,
    AsusRouterNotImplementedError,
    AsusRouterSSLCertificateError,
    AsusRouterTimeoutError,
)
from asusrouter.modules.endpoint import (
    EndpointService,
    EndpointType,
    is_sensitive_endpoint,
)
from asusrouter.modules.endpoint.error import handle_access_error
from asusrouter.tools.connection import get_cookie_jar
from asusrouter.tools.converters import clean_string
from asusrouter.tools.security import ARSecurityLevel

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")


class ConnectionFallback(StrEnum):
    """Connection fallback strategies."""

    HTTP = "http"
    HTTPS = "https"
    HTTPS_UNSAFE = "https_unsafe"


def generate_credentials(
    username: str, password: str
) -> tuple[str, dict[str, str]]:
    """Generate credentials for connection."""

    auth = f"{username}:{password}".encode("ascii")
    logintoken = base64.b64encode(auth).decode("ascii")
    payload = f"login_authorization={logintoken}"
    headers = {"user-agent": USER_AGENT}

    return payload, headers


class Connection:  # pylint: disable=too-many-instance-attributes
    """A connection between the library and the device."""

    def __init__(  # noqa: PLR0913
        self,
        hostname: str,
        username: str,
        password: str,
        port: int | None = None,
        use_ssl: bool = False,
        session: aiohttp.ClientSession | None = None,
        timeout: int | None = DEFAULT_TIMEOUT,
        dumpback: Callable[..., Awaitable[None]] | None = None,
        config: dict[ARCCKey, Any] | None = None,
    ):
        """Initialize connection."""

        _LOGGER.debug("Initializing a new connection to `%s`", hostname)

        # Initialize configs
        self._config = ARConnectionConfig()
        self._used_fallbacks: dict[ConnectionFallback, bool] = {}

        # Initialize startup configs if any provided
        if isinstance(config, dict):
            _LOGGER.debug("Using provided connection config: %s", config)
            for key, value in config.items():
                self._config.set(key, value)

        # Initialize parameters for connection
        self._token: str | None = None
        self._header: dict[str, str] | None = None
        self._connected: bool = False
        self._connection_lock: asyncio.Lock = asyncio.Lock()
        self._timeout: int = timeout or DEFAULT_TIMEOUT

        # Hostname and credentials
        self._hostname = hostname
        self._username = username
        self._password = password

        # Set the port and protocol based on the input
        self.config.set(
            ARCCKey.PORT,
            port or (DEFAULT_PORT_HTTPS if use_ssl else DEFAULT_PORT_HTTP),
        )
        self.config.set(ARCCKey.USE_SSL, use_ssl)
        _LOGGER.debug(
            "Using `%s` and port `%s` with ssl flag `%s`",
            self.http,
            self.config.get(ARCCKey.PORT),
            use_ssl,
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

    async def __aenter__(self) -> Self:
        """Enter the connection."""

        await self.async_connect()
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        """Exit the connection."""

        await self.async_close()

    @classmethod
    async def create(  # noqa: PLR0913
        cls,
        hostname: str,
        username: str,
        password: str,
        port: int | None = None,
        use_ssl: bool = False,
        session: aiohttp.ClientSession | None = None,
        timeout: int | None = DEFAULT_TIMEOUT,  # noqa: ASYNC109
        dumpback: Callable[..., Awaitable[None]] | None = None,
        config: dict[ARCCKey, Any] | None = None,
    ) -> Connection:
        """Create and initialize a connection."""

        connection = cls(
            hostname=hostname,
            username=username,
            password=password,
            port=port,
            use_ssl=use_ssl,
            session=session,
            timeout=timeout or DEFAULT_TIMEOUT,
            dumpback=dumpback,
            config=config,
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
            connector=aiohttp.TCPConnector(),
            cookie_jar=get_cookie_jar(),
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

    async def async_connect(self, lock: asyncio.Lock | None = None) -> bool:
        """Connect to the device and get a new auth token."""

        try:
            await asyncio.wait_for(
                self._async_connect_with_lock(lock), timeout=self._timeout
            )
            return True
        except TimeoutError:
            _LOGGER.error("Connection to %s timed out", self._hostname)
            return False

    async def _async_connect_with_lock(
        self,
        lock: asyncio.Lock | None = None,
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

    def _payload_for_logging(
        self, security_level: Any, endpoint: EndpointType, payload: str | None
    ) -> str | None:
        """Return the payload to log if any.

        Rules:
        - STRICT: never log payload
        - DEFAULT: log only non-sensitive endpoints
        - SANITIZED: (not implemented)
            log sensitive endpoints with automatic redaction
        - UNSAFE: log sensitive endpoints verbatim
        """

        # Resolve security level safely
        level = ARSecurityLevel.from_value(security_level)

        # STRICT: never include payload
        if level == ARSecurityLevel.STRICT:
            return None

        # Clean from empty strings
        payload = clean_string(payload)

        # Always null login endpoint payload
        if endpoint == EndpointService.LOGIN:
            return None

        # Remove sensitive information
        if is_sensitive_endpoint(endpoint):
            if level == ARSecurityLevel.SANITIZED:
                # TODO: Not implemented yet
                return "[SANITIZED PLACEHOLDER]"
            if ARSecurityLevel.above_sanitized(level):
                return payload
            return None

        # Non-sensitive endpoints: include payload when available
        return payload if payload is not None else None

    def _log_request(
        self, endpoint: EndpointType, payload: str | None
    ) -> None:
        """Log the request details."""

        security_level = ARConfig.get(ARConfigKey.DEBUG_PAYLOAD)

        # Prepare payload to log
        payload_to_log = self._payload_for_logging(
            security_level, endpoint, payload
        )

        if payload_to_log is None:
            _LOGGER.debug("Sending request to `%s`", endpoint)
        else:
            _LOGGER.debug(
                "Sending request to `%s` with payload: %s",
                endpoint,
                payload_to_log,
            )

    async def _send_request(  # noqa: C901, PLR0912
        self,
        endpoint: EndpointType,
        payload: str | None = None,
        headers: dict[str, str] | None = None,
        request_type: RequestType = RequestType.POST,
    ) -> tuple[int, dict[str, str], str]:
        """Send a request to the device."""

        # Send request
        try:
            # Log request
            self._log_request(endpoint, payload)

            # Make the request
            resp_status, resp_headers, resp_content = await self._make_request(
                endpoint,
                payload,
                headers,
                request_type,
            )

            # Raise exception on 404
            if resp_status == HTTPStatus.NOT_FOUND:
                raise AsusRouter404Error(f"Endpoint {endpoint} not found")

            # Raise exception on non-200 status
            if resp_status != HTTPStatus.OK:
                raise AsusRouterAccessError(
                    f"Cannot access {endpoint}, status {resp_status}"
                )

            # Check for access errors
            if "error_status" in resp_content:
                handle_access_error(
                    endpoint, resp_status, resp_headers, resp_content
                )

            # Reset fallback tracker if multiple fallbacks are allowed
            if self.config.get(ARCCKey.ALLOW_MULTIPLE_FALLBACKS):
                self._used_fallbacks.clear()

            # Return the response
            return (resp_status, resp_headers, resp_content)
        except ssl.SSLCertVerificationError as ex:
            if self.config.get(ARCCKey.STRICT_SSL) is False:
                _LOGGER.warning(
                    "Cannot verify SSL certificate. Since `STRICT_SSL` "
                    "configuration is disabled, falling back to HTTP "
                    "with a default port"
                )
                await self._fallback()
                # Repeat the attempt
                return await self._send_request(
                    endpoint, payload, headers, request_type
                )
            raise AsusRouterSSLCertificateError(
                "SSL certificate verification failed. Your configuration "
                "requires a strict SSL certificate verification."
            ) from ex
        except aiohttp.ClientConnectorError as ex:
            # Are automatic fallbacks allowed?
            if self.config.get(ARCCKey.ALLOW_FALLBACK):
                return await self._async_handle_fallback(
                    callback=self._send_request,
                    endpoint=endpoint,
                    payload=payload,
                    headers=headers,
                    request_type=request_type,
                )

            self.reset_connection()
            raise AsusRouterConnectionError(
                f"Cannot connect to `{self._hostname}` on port "
                f"`{self.port}`. Failed in `_send_request` with error: `{ex}`"
            ) from ex
        except (aiohttp.ClientConnectionError, aiohttp.ClientOSError) as ex:
            raise AsusRouterConnectionError(
                f"Cannot connect to `{self._hostname}` on port "
                f"`{self.port}`. Failed in `_send_request` with error: `{ex}`"
            ) from ex
        except (TimeoutError, asyncio.CancelledError) as ex:
            raise AsusRouterTimeoutError(
                f"Data cannot be retrieved due to an asyncio error. "
                f"Connection failed: {ex}"
            ) from ex
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.debug(
                "Unexpected error sending request to %s: %s",
                endpoint,
                ex,
            )
            raise ex

    async def _async_handle_fallback(
        self, callback: Callable[..., Awaitable[_T]], **kwargs: Any
    ) -> _T:
        """Handle fallbacks on sending requests.

        The matrix for the automatic feedback is as follows:

        | Con @ Port      | New @ port      | Required config             |
        | --------------- | --------------- | --------------------------- |
        | HTTPS @ Custom  | HTTPS @ Default |                             |
        | HTTPS @ Default | HTTP @ Default  | STRICT_SSL not set          |
        | HTTP @ Custom   | HTTP @ Default  |                             |
        | HTTP @ Default  | HTTPS @ Default | ALLOW_UPGRADE_HTTP_TO_HTTPS |
        """

        if self.config.get(ARCCKey.USE_SSL):
            # From custom HTTPS to default HTTPS
            if self.port != DEFAULT_PORT_HTTPS:
                if self._used_fallbacks.get(ConnectionFallback.HTTPS):
                    raise AsusRouterFallbackLoopError(
                        "Fallback loop detected trying to heal HTTPS "
                        f"connection with set port `{self.port}`"
                    )

                _LOGGER.warning(
                    "Cannot connect on the provided HTTPS port `%d`. "
                    "Will fallback to the default port `%d`",
                    self.port,
                    DEFAULT_PORT_HTTPS,
                )
                await self._fallback(fallback_type=ConnectionFallback.HTTPS)
                # Repeat the attempt
                return await callback(**kwargs)

            # From default HTTPS to default HTTP
            if self.config.get(ARCCKey.STRICT_SSL):
                raise AsusRouterFallbackForbiddenError(
                    "Fallback from HTTPS to HTTP connection is forbidden "
                    "by the `STRICT_SSL` configuration option"
                )
            if self._used_fallbacks.get(ConnectionFallback.HTTP):
                raise AsusRouterFallbackLoopError(
                    "Fallback loop detected trying to heal HTTPS "
                    "by switching to HTTP"
                )
            _LOGGER.warning(
                "Cannot connect on the default HTTPS port `%d`. "
                "Will fallback to the HTTP connection "
                "on default port `%d`",
                DEFAULT_PORT_HTTPS,
                DEFAULT_PORT_HTTP,
            )
            await self._fallback(fallback_type=ConnectionFallback.HTTP)
            # Repeat the attempt
            return await callback(**kwargs)

        # From custom HTTP to default HTTP
        if self.port != DEFAULT_PORT_HTTP:
            if self._used_fallbacks.get(ConnectionFallback.HTTP):
                raise AsusRouterFallbackLoopError(
                    "Fallback loop detected trying to heal HTTP "
                    "by upgrading to HTTPS"
                )

            _LOGGER.warning(
                "Cannot connect on the custom HTTP port `%d`. "
                "Will try using the default HTTP port `%d`",
                self.port,
                DEFAULT_PORT_HTTP,
            )
            await self._fallback(fallback_type=ConnectionFallback.HTTP)
            # Repeat the attempt
            return await callback(**kwargs)

        # From default HTTP to default HTTPS
        if self.config.get(ARCCKey.ALLOW_UPGRADE_HTTP_TO_HTTPS):
            # Force certificate verification
            self.config.set(ARCCKey.VERIFY_SSL, True)
            if self._used_fallbacks.get(ConnectionFallback.HTTPS):
                raise AsusRouterFallbackLoopError(
                    "Fallback loop detected trying to heal HTTP "
                    "by upgrading to HTTPS"
                )

            _LOGGER.warning(
                "Cannot connect on the default HTTP port `%d`. "
                "Will try upgrading to the default HTTPS port `%d`",
                self.port,
                DEFAULT_PORT_HTTPS,
            )
            await self._fallback(fallback_type=ConnectionFallback.HTTPS)
            # Repeat the attempt
            return await callback(**kwargs)

        raise AsusRouterFallbackError(
            "Automatic fallback failed. Consider disabling it."
        )

    async def _fallback(
        self, fallback_type: ConnectionFallback | None = None
    ) -> None:
        """Perform connection fallback."""

        if not fallback_type:
            fallback_type = ConnectionFallback.HTTP

        # Mark fallback type as used to avoid loops
        self._used_fallbacks[fallback_type] = True

        # Set fallback connection parameters
        match fallback_type:
            case ConnectionFallback.HTTP:
                self.config.set(ARCCKey.USE_SSL, False)
                self.config.set(ARCCKey.PORT, DEFAULT_PORT_HTTP)
                # We should not change the VERIFY_SSL setting here

            case ConnectionFallback.HTTPS:
                self.config.set(ARCCKey.USE_SSL, True)
                self.config.set(ARCCKey.PORT, DEFAULT_PORT_HTTPS)
                # We should not change the VERIFY_SSL setting here

            case ConnectionFallback.HTTPS_UNSAFE:
                self.config.set(ARCCKey.USE_SSL, True)
                self.config.set(ARCCKey.PORT, DEFAULT_PORT_HTTPS)
                self.config.set(ARCCKey.VERIFY_SSL, False)

            case _:
                raise AsusRouterNotImplementedError(
                    f"Connection fallback not implemented: {fallback_type}"
                )

        # Reconnect with new parameters
        self.reset_connection()
        await self.async_connect()

    async def async_query(
        self,
        endpoint: EndpointType,
        payload: str | None = None,
        headers: dict[str, str] | None = None,
        request_type: RequestType = RequestType.POST,
    ) -> tuple[int, dict[str, str], str]:
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
        payload: str | None = None,
        headers: dict[str, str] | None = None,
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
        url = f"{self.http}://{self._hostname}:{self.port}/{endpoint.value}"

        # Add get parameters if needed
        if request_type == RequestType.GET and payload:
            url_payload = payload.replace(";", "&")
            url = f"{url}?{url_payload}"

        # Process the payload to be sent
        payload_to_send = quote(payload) if payload else None

        # Send the request
        async with self._session.request(
            request_type.value,
            url,
            data=payload_to_send if request_type == RequestType.POST else None,
            headers=headers,
            ssl=self.config.get(ARCCKey.VERIFY_SSL),
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
    def config(self) -> ARConnectionConfig:
        """Return connection config."""

        return self._config

    @property
    def connected(self) -> bool:
        """Return connection status."""

        return self._connected

    @property
    def http(self) -> str:
        """Return HTTP scheme."""

        return "https" if self._config.get(ARCCKey.USE_SSL) else "http"

    @property
    def port(self) -> int:
        """Return port number."""

        return safe_int_config(self._config.get(ARCCKey.PORT))
