"""Connection module.

This module handles the connection between the library and the router
as well as all the data transfer.
"""

from __future__ import annotations

import asyncio
import base64
from collections.abc import Awaitable, Callable
import contextlib
from enum import StrEnum
import json
import logging
import ssl
from typing import Any, Self, TypeVar
from urllib.parse import quote

import aiohttp

from asusrouter.config import (
    ARConfig,
    ARConfigKey as ARConfKey,
    safe_int_config,
)
from asusrouter.config.connection import (
    ARConnectionConfig,
    ARConnectionConfigKey as ARCCKey,
)
from asusrouter.const import (
    DEFAULT_PORT_HTTP,
    DEFAULT_PORT_HTTPS,
    DEFAULT_TIMEOUT,
    DEFAULT_TIMEOUT_FALLBACK,
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
    AsusRouterSSLCertificateError,
    AsusRouterTimeoutError,
)
from asusrouter.modules.endpoint.error import handle_access_error
from asusrouter.modules.endpoint_v2 import AREndpoint, get_endpoint_sensitive
from asusrouter.tools.connection import get_cookie_jar
from asusrouter.tools.converters_v2.raw import raw_to_str
from asusrouter.tools.security import ARSecurityLevel

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")


class ConnectionFallback(StrEnum):
    """Connection fallback strategies."""

    HTTP = "http"
    HTTPS = "https"


def generate_credentials(
    username: str, password: str
) -> tuple[str, dict[str, str]]:
    """Generate credentials for connection."""

    auth = f"{username}:{password}".encode("ascii")
    logintoken = base64.b64encode(auth).decode("ascii")
    payload = f"login_authorization={logintoken}"
    headers = {"user-agent": USER_AGENT}

    return payload, headers


def sanitize_data(
    value: str | None,
) -> str:
    """Sanitize data placeholder."""

    return "[SANITIZED PLACEHOLDER]"


def _payload_for_logging(
    security_level: Any, endpoint: AREndpoint, payload: str | None
) -> str | None:
    """Return the payload to log if any.

    Rules:
    - STRICT: never log payload
    - DEFAULT: log only non-sensitive endpoints
    - SANITIZED: log sensitive endpoints with automatic sanitization
    - UNSAFE: log sensitive endpoints verbatim
    """

    level = ARSecurityLevel.from_value(security_level)

    # Login payload is never logged regardless of security level.
    if level == ARSecurityLevel.STRICT or endpoint == AREndpoint.LOGIN:
        return None

    payload = raw_to_str(payload)
    if payload is None:
        return None

    if get_endpoint_sensitive(endpoint):
        if ARSecurityLevel.at_least_sanitized(level):
            if level == ARSecurityLevel.SANITIZED:
                return sanitize_data(payload)
            return payload
        return None

    return payload


def _log_request(endpoint: AREndpoint, payload: str | None) -> None:
    """Log the request details."""

    # Skip all payload resolution work when debug logging is disabled.
    # _payload_for_logging converts the payload and resolves security
    # levels — wasted effort if the result is never emitted.
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return

    security_level = ARConfig.get(ARConfKey.DEBUG_PAYLOAD)
    payload_to_log = _payload_for_logging(security_level, endpoint, payload)

    if payload_to_log is None:
        _LOGGER.debug("Sending request to `%s`", endpoint)
    else:
        _LOGGER.debug(
            "Sending request to `%s` with payload: %s",
            endpoint,
            payload_to_log,
        )


def _check_response(
    endpoint: AREndpoint,
    resp_status: int,
    resp_headers: Any,
    resp_content: str,
) -> None:
    """Raise on error HTTP responses."""

    if resp_status == HTTPStatus.NOT_FOUND:
        raise AsusRouter404Error(f"Endpoint {endpoint} not found")
    if resp_status != HTTPStatus.OK:
        raise AsusRouterAccessError(
            f"Cannot access {endpoint}, status {resp_status}"
        )
    if "error_status" in resp_content:
        handle_access_error(endpoint, resp_status, resp_headers, resp_content)


class Connection:  # pylint: disable=too-many-instance-attributes
    """A connection between the library and the device."""

    # ---------------------------
    # Init / Context manager -->
    # ---------------------------

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

        self._config = ARConnectionConfig()
        self._used_fallbacks: set[ConnectionFallback] = set()

        self._token: str | None = None
        self._header: dict[str, str] | None = None
        self._connected: bool = False
        self._connection_lock: asyncio.Lock = asyncio.Lock()
        self._timeout: int = timeout or DEFAULT_TIMEOUT

        # Single in-flight connect task (serialize connection attempts)
        self._connect_task: asyncio.Task[bool] | None = None
        # Lock to guard creation of the connect task
        self._connect_task_lock: asyncio.Lock = asyncio.Lock()

        self._hostname: str = hostname
        self._username: str = username
        self._password: str = password
        self._auth_payload, self._auth_headers = generate_credentials(
            username, password
        )

        self.config.set(
            ARCCKey.PORT,
            port or (DEFAULT_PORT_HTTPS if use_ssl else DEFAULT_PORT_HTTP),
        )
        self.config.set(ARCCKey.USE_SSL, use_ssl)

        if config is not None:
            _LOGGER.debug("Using provided connection config: %s", config)
            for key, value in config.items():
                self._config.set(key, value)

        _LOGGER.debug(
            "Using `%s` and port `%s` with ssl flag `%s`",
            self.http,
            self.config.get(ARCCKey.PORT),
            self.config.get(ARCCKey.USE_SSL),
        )

        self._dumpback = dumpback

        self._manage_session: bool = False
        self._session: aiohttp.ClientSession | None = session
        if session is not None:
            _LOGGER.debug("Using provided session")
        else:
            _LOGGER.debug("No session provided. Will create on connect")

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

        await self.async_close_session()

    # ---------------------------
    # <-- Init / Context manager
    # ---------------------------

    # ---------------------------
    # Properties -->
    # ---------------------------

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

    @property
    def webpanel(self) -> str:
        """Return web panel URL."""

        return f"{self.http}://{self._hostname}:{self.port}"

    # ---------------------------
    # <-- Properties
    # ---------------------------

    # ---------------------------
    # Session management -->
    # ---------------------------

    def _create_session(self) -> aiohttp.ClientSession:
        """Create a new session."""

        self._manage_session = True
        return aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(),
            cookie_jar=get_cookie_jar(),
            timeout=aiohttp.ClientTimeout(total=self._timeout),
        )

    async def async_close_session(self) -> None:
        """Close the session."""

        if not self._manage_session or not self._session:
            _LOGGER.debug("No session to close or not managing the session")
            return
        if not self._session.closed:
            _LOGGER.debug("Closing the session")
            await self._session.close()
        else:
            _LOGGER.debug("Session already closed")

    # ---------------------------
    # <-- Session management
    # ---------------------------

    # ---------------------------
    # Connection management -->
    # ---------------------------

    async def async_connect(
        self,
        t_overwrite: float | None = None,
        block_error: bool = False,
    ) -> bool:
        """Connect to the device and get a new auth token."""

        if self._connected:
            return True

        timeout = t_overwrite or self._timeout

        task = await self._ensure_connect_task()
        if task is None:
            return True

        try:
            # Await the in-flight connect but don't cancel it on
            # outer timeout: use shield so that callers timing out
            # won't cancel the actual attempt.
            return await asyncio.wait_for(
                asyncio.shield(task), timeout=timeout
            )
        except TimeoutError:
            if not block_error:
                _LOGGER.error("Connection to %s timed out", self._hostname)
            # do not cancel the underlying task here; let it finish
            # and satisfy future callers
            return False
        except asyncio.CancelledError:
            # Propagate outer cancellations (e.g. app shutdown).
            # Only swallow if the inner task itself was cancelled.
            current = asyncio.current_task()
            if current is not None and current.cancelling() > 0:
                raise
            if not block_error:
                _LOGGER.debug("Connection attempt was cancelled")
            return False
        finally:
            self._clear_connect_task(task)

    async def _ensure_connect_task(self) -> asyncio.Task[bool] | None:
        """Return the in-flight connect Task, creating one if needed.

        Returns None if the connection is already established.
        """
        async with self._connect_task_lock:
            if self._connected:
                return None
            if self._connect_task is not None and self._connect_task.done():
                if not self._connect_task.cancelled():
                    with contextlib.suppress(Exception):
                        self._connect_task.result()
                self._connect_task = None
            if self._connect_task is None:
                self._connect_task = asyncio.create_task(self._login())
            # Capture before releasing the lock: another coroutine's
            # _clear_connect_task could set self._connect_task = None
            # between the lock exit and asyncio.shield() in async_connect.
            return self._connect_task

    def _clear_connect_task(self, task: asyncio.Task[bool]) -> None:
        """Clear a finished connect Task and consume its exception if any."""

        if task.done() and self._connect_task is task:
            # Consume unhandled exception to prevent "never retrieved" noise.
            # Skip cancelled tasks — CancelledError is not an Exception.
            if not task.cancelled():
                with contextlib.suppress(Exception):
                    task.result()
            self._connect_task = None

    async def _login(self) -> bool:
        """Send the login request and update auth state on success.

        Acquires the lock only for state checks and updates. Network IO
        runs outside the lock to avoid deadlocks when fallback triggers
        a nested connect attempt.
        """
        async with self._connection_lock:
            if self._connected:
                _LOGGER.debug("Already connected to %s", self._hostname)
                return True
            _LOGGER.debug("Initializing connection to %s", self._hostname)

        payload, headers = self._auth_payload, self._auth_headers

        try:
            _LOGGER.debug("Requesting authorization")
            _, _, resp_content = await self._send_request(
                AREndpoint.LOGIN, payload, headers
            )
            _LOGGER.debug("Received authorization response")
        except AsusRouterSSLCertificateError as ex:
            raise AsusRouterAccessError(
                f"Cannot access {AREndpoint.LOGIN} "
                "due to the SSL certificate error"
            ) from ex
        except AsusRouterError as ex:
            _LOGGER.debug(
                "Connection to %s failed with error: %s", self._hostname, ex
            )
            raise
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.debug(
                "Unexpected error while connecting to %s: %s",
                self._hostname,
                ex,
            )
            raise

        try:
            token = json.loads(resp_content).get("asus_token")
        except (json.JSONDecodeError, AttributeError):
            _LOGGER.error("Invalid login response from %s", self._hostname)
            return False
        if not token:
            _LOGGER.error("No token received")
            return False

        async with self._connection_lock:
            if not self._connected:
                self._token = token
                self._header = {
                    "user-agent": USER_AGENT,
                    "cookie": f"asus_token={token}",
                }
                self._connected = True
                _LOGGER.debug("Connected to %s", self._hostname)

        return True

    async def async_disconnect(self) -> bool:
        """Disconnect from the device."""

        if not self._connected:
            _LOGGER.debug("Not connected to %s", self._hostname)
            return True

        _LOGGER.debug("Initializing disconnection from %s", self._hostname)

        # Cancel any in-flight connect task so it can't re-establish
        # connection state after we tear it down.
        old_task: asyncio.Task[bool] | None = None
        async with self._connect_task_lock:
            if (
                self._connect_task is not None
                and not self._connect_task.done()
            ):
                old_task = self._connect_task
                self._connect_task = None
                old_task.cancel()

        if old_task is not None:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await old_task

        try:
            await self._send_request(AREndpoint.LOGOUT)
        except AsusRouterLogoutError:
            # Router signals successful logout with an error response
            self.reset_auth()
            _LOGGER.debug("Disconnected from %s", self._hostname)
            return True
        except AsusRouterError as ex:
            _LOGGER.debug(
                "Error while disconnecting from %s: %s", self._hostname, ex
            )
            return False

        # Router returned a non-error response — unexpected but auth is gone.
        self.reset_auth()
        _LOGGER.debug("Disconnected from %s", self._hostname)
        return True

    def reset_auth(self) -> None:
        """Clear auth state when the connection is no longer valid."""

        if not self._connected:
            return

        _LOGGER.debug("Resetting connection to %s", self._hostname)

        self._connected = False
        self._token = None
        self._header = None

    # ---------------------------
    # <-- Connection management
    # ---------------------------

    # ---------------------------
    # Request handling -->
    # ---------------------------

    async def _ensure_session(self) -> None:
        """Ensure a live HTTP session exists, creating one if needed."""

        if self._session is None:
            _LOGGER.debug("No session available. Creating a new one")
            self._session = self._create_session()
        elif self._session.closed:
            _LOGGER.debug(
                "Session closed. Creating new session and reconnecting"
            )
            self.reset_auth()
            self._session = self._create_session()
            # If called from within the in-flight login task, awaiting
            # async_connect() would await the current task itself and
            # deadlock until the outer timeout fires. The ongoing login
            # proceeds on the fresh session, so skip the nested reconnect.
            if asyncio.current_task() is self._connect_task:
                return
            await self.async_connect()
            if not self._connected:
                raise AsusRouterTimeoutError(
                    "Connection timed out — could not reconnect after "
                    "session was closed"
                )

    async def async_query(
        self,
        endpoint: AREndpoint,
        payload: str | None = None,
        headers: dict[str, str] | None = None,
        request_type: RequestType = RequestType.POST,
    ) -> tuple[int, dict[str, str], str]:
        """Send a request to the device."""

        if not self._connected:
            _LOGGER.debug("Not connected to %s. Connecting...", self._hostname)
            await self.async_connect()

        if not self._connected:
            raise AsusRouterTimeoutError(
                "Connection timed out — could not establish initial connection"
            )

        _LOGGER.debug(
            "Sending `%s` request to `%s`", request_type, self._hostname
        )
        return await self._send_request(
            endpoint, payload, headers, request_type
        )

    async def _send_request(
        self,
        endpoint: AREndpoint,
        payload: str | None = None,
        headers: dict[str, str] | None = None,
        request_type: RequestType = RequestType.POST,
    ) -> tuple[int, dict[str, str], str]:
        """Dispatch request with session recovery, status checks, fallbacks."""

        await self._ensure_session()

        try:
            _log_request(endpoint, payload)

            resp_status, resp_headers, resp_content = await self._make_request(
                endpoint, payload, headers, request_type
            )

            _check_response(endpoint, resp_status, resp_headers, resp_content)

            if self._used_fallbacks:
                if not self.config.get(ARCCKey.ALLOW_MULTIPLE_FALLBACKS):
                    # Config discovery complete — lock connection parameters
                    # so no further fallbacks alter the working config.
                    self.config.set(ARCCKey.ALLOW_FALLBACK, False)
                self._used_fallbacks.clear()

            return (resp_status, resp_headers, resp_content)

        except aiohttp.ClientConnectorError as ex:
            return await self._handle_connector_error(
                ex, endpoint, payload, headers, request_type
            )

        except (aiohttp.ClientConnectionError, aiohttp.ClientOSError) as ex:
            raise AsusRouterConnectionError(
                f"Cannot connect to `{self._hostname}` on port "
                f"`{self.port}`. Failed in `_send_request` with error: `{ex}`"
            ) from ex

        except TimeoutError as ex:
            raise AsusRouterTimeoutError(
                "Data cannot be retrieved due to an asyncio error. "
                f"Connection failed: {ex}"
            ) from ex

        except AsusRouterError:
            raise

        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.debug(
                "Unexpected error sending request to %s: %s",
                self._hostname,
                ex,
            )
            raise

    async def _handle_connector_error(
        self,
        ex: aiohttp.ClientConnectorError,
        endpoint: AREndpoint,
        payload: str | None,
        headers: dict[str, str] | None,
        request_type: RequestType,
    ) -> tuple[int, dict[str, str], str]:
        """Route a ClientConnectorError to the appropriate handler.

        Detects SSL certificate verification errors and handles them
        separately from general connectivity failures.
        """

        if isinstance(ex, aiohttp.ClientConnectorSSLError) and isinstance(
            ex.os_error, ssl.SSLCertVerificationError
        ):
            if not self.config.get(ARCCKey.STRICT_SSL) and self.config.get(
                ARCCKey.ALLOW_FALLBACK
            ):
                _LOGGER.warning(
                    "Cannot verify SSL certificate. Since `STRICT_SSL` "
                    "configuration is disabled, falling back to HTTP "
                    "with a default port"
                )
                self._used_fallbacks.add(ConnectionFallback.HTTPS)
                await self._apply_fallback(
                    {ARCCKey.USE_SSL: False, ARCCKey.PORT: DEFAULT_PORT_HTTP}
                )
                return await self._send_request(
                    endpoint, payload, headers, request_type
                )
            raise AsusRouterSSLCertificateError(
                "SSL certificate verification failed. Your configuration "
                "requires a strict SSL certificate verification."
            ) from ex
        if self.config.get(ARCCKey.ALLOW_FALLBACK):
            return await self._handle_fallback(
                callback=self._send_request,
                endpoint=endpoint,
                payload=payload,
                headers=headers,
                request_type=request_type,
            )
        self.reset_auth()
        raise AsusRouterConnectionError(
            f"Cannot connect to `{self._hostname}` on port "
            f"`{self.port}`. Failed in `_send_request` with error: `{ex}`"
        ) from ex

    async def _make_request(
        self,
        endpoint: AREndpoint,
        payload: str | None = None,
        headers: dict[str, str] | None = None,
        request_type: RequestType = RequestType.POST,
    ) -> tuple[int, Any, str]:
        """Make an HTTP request and return raw (status, headers, content)."""

        if headers is None:
            headers = self._header

        url = f"{self.webpanel}/{endpoint.value}"

        if request_type == RequestType.GET and payload:
            url = f"{url}?{payload.replace(';', '&')}"

        if request_type == RequestType.POST:
            payload_to_send = quote(payload) if payload else None
        else:
            payload_to_send = None

        async with self._session.request(  # type: ignore[union-attr]
            request_type.value,
            url,
            data=payload_to_send,
            headers=headers,
            ssl=self.config.get(ARCCKey.VERIFY_SSL),
        ) as response:
            resp_status = response.status
            resp_headers = response.headers
            try:
                resp_content = await response.text()
            except UnicodeDecodeError:
                _LOGGER.debug("Cannot decode response. Will ignore errors")
                resp_content = await response.text(errors="ignore")

            if self._dumpback is not None:
                await self._dumpback(
                    endpoint, payload, resp_status, resp_headers, resp_content
                )

            return (resp_status, resp_headers, resp_content)

    # ---------------------------
    # <-- Request handling
    # ---------------------------

    # ---------------------------
    # Fallback handling -->
    # ---------------------------

    def _next_fallback_config(self) -> dict[ARCCKey, Any]:
        """Return config delta for the next fallback transition.

        Reads current connection state, checks loop detection and
        constraints, logs the transition, marks the fallback as used,
        and returns the config keys to apply.

        Fallback matrix:
        | Current             | Next            | Guard                   |
        | ------------------- | --------------- | ----------------------- |
        | HTTPS @ custom port | HTTPS @ default |                         |
        | HTTPS @ default     | HTTP @ default  | STRICT_SSL not set      |
        | HTTP @ custom port  | HTTP @ default  |                         |
        | HTTP @ default      | HTTPS @ default | ALLOW_UPGRADE_HTTP→HTTPS|
        """

        use_ssl = self.config.get(ARCCKey.USE_SSL)
        port = self.port

        if use_ssl:
            if port != DEFAULT_PORT_HTTPS:
                if ConnectionFallback.HTTPS in self._used_fallbacks:
                    raise AsusRouterFallbackLoopError(
                        "Fallback loop detected trying to heal HTTPS "
                        f"connection with set port `{port}`"
                    )
                _LOGGER.warning(
                    "Cannot connect on the provided HTTPS port `%d`. "
                    "Will fallback to the default port `%d`",
                    port,
                    DEFAULT_PORT_HTTPS,
                )
                self._used_fallbacks.add(ConnectionFallback.HTTPS)
                return {
                    ARCCKey.USE_SSL: True,
                    ARCCKey.PORT: DEFAULT_PORT_HTTPS,
                }

            if self.config.get(ARCCKey.STRICT_SSL):
                raise AsusRouterFallbackForbiddenError(
                    "Fallback from HTTPS to HTTP connection is forbidden "
                    "by the `STRICT_SSL` configuration option"
                )
            if ConnectionFallback.HTTP in self._used_fallbacks:
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
            self._used_fallbacks.add(ConnectionFallback.HTTP)
            return {ARCCKey.USE_SSL: False, ARCCKey.PORT: DEFAULT_PORT_HTTP}

        if port != DEFAULT_PORT_HTTP:
            if ConnectionFallback.HTTP in self._used_fallbacks:
                raise AsusRouterFallbackLoopError(
                    "Fallback loop detected trying to heal HTTP "
                    f"connection with set port `{port}`"
                )
            _LOGGER.warning(
                "Cannot connect on the custom HTTP port `%d`. "
                "Will try using the default HTTP port `%d`",
                port,
                DEFAULT_PORT_HTTP,
            )
            self._used_fallbacks.add(ConnectionFallback.HTTP)
            return {ARCCKey.USE_SSL: False, ARCCKey.PORT: DEFAULT_PORT_HTTP}

        if not self.config.get(ARCCKey.ALLOW_UPGRADE_HTTP_TO_HTTPS):
            raise AsusRouterFallbackError(
                "Cannot connect on HTTP — no further fallback options. "
                "Enable `ALLOW_UPGRADE_HTTP_TO_HTTPS` to allow HTTPS upgrade."
            )
        if ConnectionFallback.HTTPS in self._used_fallbacks:
            raise AsusRouterFallbackLoopError(
                "Fallback loop detected trying to upgrade HTTP to HTTPS"
            )
        _LOGGER.warning(
            "Cannot connect on the default HTTP port `%d`. "
            "Will try upgrading to the default HTTPS port `%d`",
            DEFAULT_PORT_HTTP,
            DEFAULT_PORT_HTTPS,
        )
        self._used_fallbacks.add(ConnectionFallback.HTTPS)
        return {
            ARCCKey.USE_SSL: True,
            ARCCKey.PORT: DEFAULT_PORT_HTTPS,
        }

    async def _apply_fallback(self, config: dict[ARCCKey, Any]) -> None:
        """Apply fallback config, then reconnect unless in login context.

        Sets each config key, cancels any in-flight connect task (skipping
        self-cancel when called from within the login task), resets auth
        state, and reconnects with a short fallback timeout.

        When called from within the active login task (login context),
        skips the reconnect step entirely — _login retries _send_request
        directly on the updated config, so no extra login request is made.
        _connect_task is left pointing to the current task so that any
        further fallbacks in the same login chain also detect login context.
        """

        for key, value in config.items():
            self.config.set(key, value)

        current = asyncio.current_task()
        old_task: asyncio.Task[bool] | None = None
        login_context = False
        async with self._connect_task_lock:
            if (
                self._connect_task is not None
                and not self._connect_task.done()
            ):
                old_task = self._connect_task
                if old_task is current:
                    login_context = True
                    # Leave _connect_task as-is so the next fallback
                    # call in this login chain also detects login context.
                else:
                    self._connect_task = None
                    _LOGGER.debug(
                        "Cancelling in-flight connect attempt to "
                        "allow fallback reconnect"
                    )
                    old_task.cancel()

        if old_task is not None and not login_context:

            def _log_task_exc(task: asyncio.Task[bool]) -> None:
                if not task.cancelled() and (exc := task.exception()):
                    _LOGGER.debug(
                        "In-flight connect task raised after cancel: %s",
                        exc,
                    )

            old_task.add_done_callback(_log_task_exc)
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await old_task

        self.reset_auth()
        if login_context:
            # Config is updated. _login will retry _send_request on the
            # new config — a separate reconnect here would add a redundant
            # login request.
            return
        if not await self.async_connect(
            t_overwrite=DEFAULT_TIMEOUT_FALLBACK, block_error=True
        ):
            raise AsusRouterConnectionError(
                f"Fallback reconnect to `{self._hostname}` failed"
            )

    async def _handle_fallback(
        self, callback: Callable[..., Awaitable[_T]], **kwargs: Any
    ) -> _T:
        """Select next fallback config, apply it, and retry callback."""

        config = self._next_fallback_config()
        await self._apply_fallback(config)
        return await callback(**kwargs)

    # ---------------------------
    # <-- Fallback handling
    # ---------------------------
