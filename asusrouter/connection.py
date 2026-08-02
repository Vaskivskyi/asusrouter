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

from asusrouter.config import safe_int_config
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
from asusrouter.modules.endpoint import (
    AREndpoint,
    get_endpoint_payload_sensitivity,
    get_endpoint_raw_payload,
)
from asusrouter.modules.endpoint.error import (
    ARAccessError,
    handle_access_error,
)
from asusrouter.tools.converters.raw import raw_to_str
from asusrouter.tools.identifiers import Hostname
from asusrouter.tools.security import Sensitive
from asusrouter.tools.security.log import render_for_log

_LOGGER = logging.getLogger(__name__)

# A credential change bounces. Wait and try to reconnect
# Fix attempts so we don't hit captcha or lockout on fail
_CREDENTIALS_RECONNECT_INITIAL_DELAY: float = 5.0
_CREDENTIALS_RECONNECT_INTERVAL: float = 5.0
_CREDENTIALS_RECONNECT_MAX_ATTEMPTS: int = 3

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


def _consume_task_exception(task: asyncio.Task[bool]) -> None:
    """Retrieve a finished task's exception so asyncio does not log it."""

    if not task.cancelled():
        with contextlib.suppress(Exception):
            task.exception()


def _log_request(endpoint: AREndpoint, payload: str | None) -> None:
    """Log the request details.

    The payload is wrapped as a `Sensitive` value carrying the endpoint's
    payload sensitivity; the log masking filter redacts it below that level.
    """

    # Skip payload work when debug logging is disabled
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return

    payload = raw_to_str(payload)
    if payload is None:
        _LOGGER.debug("Sending request to `%s`", endpoint)
        return

    _LOGGER.debug(
        "Sending request to `%s` with payload: %s",
        endpoint,
        Sensitive(payload, get_endpoint_payload_sensitivity(endpoint)),
    )


def _access_error(error: AsusRouterAccessError) -> ARAccessError:
    """Read the access error code the exception carries."""

    for arg in error.args:
        if isinstance(arg, ARAccessError):
            return arg
    return ARAccessError.UNKNOWN


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
        response_callback: Callable[..., Awaitable[None]] | None = None,
        config: dict[ARCCKey, Any] | None = None,
    ):
        """Initialize connection."""

        # Sensitive wrapper used only for logging; requests use the raw str
        self._log_hostname = Hostname(hostname)
        _LOGGER.debug(
            "Initializing a new connection to `%s`", self._log_hostname
        )

        self._config = ARConnectionConfig()
        self._used_fallbacks: set[ConnectionFallback] = set()

        self._token: str | None = None
        self._header: dict[str, str] | None = None
        self._connected: bool = False
        # Downgrade expected connection errors to debug
        self._suppress_errors: bool = False
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

        # Bound concurrent HTTP requests; 1 keeps them fully serialized.
        # Read once here - changing the config later has no effect
        max_concurrent = max(
            1, self.config.get(ARCCKey.MAX_CONCURRENT_REQUESTS) or 1
        )
        self._request_semaphore: asyncio.Semaphore = asyncio.Semaphore(
            max_concurrent
        )

        self._response_callback = response_callback

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
    def password(self) -> str:
        """Return the current password."""

        return self._password

    @property
    def port(self) -> int:
        """Return port number."""

        return safe_int_config(self._config.get(ARCCKey.PORT))

    @property
    def username(self) -> str:
        """Return the current username."""

        return self._username

    @property
    def webpanel(self) -> str:
        """Return web panel URL."""

        return f"{self.http}://{self._hostname}:{self.port}"

    # ---------------------------
    # <-- Properties
    # ---------------------------

    # ---------------------------
    # Logging -->
    # ---------------------------

    def set_error_suppression(self, suppress: bool) -> None:
        """Downgrade expected connection errors to debug while set."""

        self._suppress_errors = suppress

    def _log_error(self, msg: str, *args: Any) -> None:
        """Log at error level, or debug while errors are suppressed."""

        _LOGGER.log(
            logging.DEBUG if self._suppress_errors else logging.ERROR,
            msg,
            *args,
        )

    # ---------------------------
    # <-- Logging
    # ---------------------------

    # ---------------------------
    # Session management -->
    # ---------------------------

    def _create_session(self) -> aiohttp.ClientSession:
        """Create a new session."""

        self._manage_session = True
        return aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(),
            cookie_jar=aiohttp.CookieJar(unsafe=True, quote_cookie=False),
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
            # Wait for the in-flight connect via asyncio.wait: unlike
            # wait_for + shield it never cancels the task on timeout and
            # never makes asyncio log the task's exception, so callers
            # timing out won't abort or noise up the actual attempt.
            # Outer cancellations (e.g. app shutdown) propagate from here.
            done, _ = await asyncio.wait({task}, timeout=timeout)
            if not done:
                if not block_error:
                    _LOGGER.error(
                        "Connection to %s timed out", self._log_hostname
                    )
                # do not cancel the underlying task here; let it finish
                # and satisfy future callers
                return False
            if task.cancelled():
                if not block_error:
                    _LOGGER.debug("Connection attempt was cancelled")
                return False
            # Re-raises the login exception to the caller if any
            return task.result()
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
                # Always retrieve the result: on an outer timeout the
                # task finishes unawaited, and its exception would otherwise be
                # logged by asyncio as "never retrieved"
                self._connect_task.add_done_callback(_consume_task_exception)
            # Capture before releasing the lock: another coroutine's
            # _clear_connect_task could set self._connect_task = None
            # between the lock exit and asyncio.wait() in async_connect.
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
                _LOGGER.debug("Already connected to %s", self._log_hostname)
                return True
            _LOGGER.debug("Initializing connection to %s", self._log_hostname)

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
                "Connection to %s failed with error: %s",
                self._log_hostname,
                ex,
            )
            raise
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.debug(
                "Unexpected error while connecting to %s: %s",
                self._log_hostname,
                ex,
            )
            raise

        try:
            token = json.loads(resp_content).get("asus_token")
        except (json.JSONDecodeError, AttributeError):
            self._log_error(
                "Invalid login response from %s", self._log_hostname
            )
            return False
        if not token:
            self._log_error("No token received")
            return False

        async with self._connection_lock:
            if not self._connected:
                self._token = token
                self._header = {
                    "user-agent": USER_AGENT,
                    "cookie": f"asus_token={token}",
                }
                self._connected = True
                _LOGGER.debug("Connected to %s", self._log_hostname)

        return True

    async def async_disconnect(self) -> bool:
        """Disconnect from the device."""

        if not self._connected:
            _LOGGER.debug("Not connected to %s", self._log_hostname)
            return True

        _LOGGER.debug("Initializing disconnection from %s", self._log_hostname)

        await self._async_cancel_connect_task()

        try:
            await self._send_request(AREndpoint.LOGOUT)
        except AsusRouterLogoutError:
            # Router signals successful logout with an error response
            self.reset_auth()
            _LOGGER.debug("Disconnected from %s", self._log_hostname)
            return True
        except AsusRouterError as ex:
            _LOGGER.debug(
                "Error while disconnecting from %s: %s",
                self._log_hostname,
                ex,
            )
            return False

        # Router returned a non-error response — unexpected but auth is gone.
        self.reset_auth()
        _LOGGER.debug("Disconnected from %s", self._log_hostname)
        return True

    async def _async_cancel_connect_task(self) -> None:
        """Cancel any in-flight connect task so it cannot re-establish auth."""

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

    def reset_auth(self) -> None:
        """Clear auth state when the connection is no longer valid."""

        if not self._connected:
            return

        _LOGGER.debug("Resetting connection to %s", self._log_hostname)

        self._connected = False
        self._token = None
        self._header = None

    async def async_set_credentials(
        self, username: str, password: str
    ) -> bool:
        """Swap the stored credentials and re-establish the session."""

        self._username = username
        self._password = password
        self._auth_payload, self._auth_headers = generate_credentials(
            username, password
        )
        # Drop the stale auth and cancel any in-flight login
        self.reset_auth()
        await self._async_cancel_connect_task()

        # httpd is restarting; expected login failures stay at debug
        prev_suppress = self._suppress_errors
        self.set_error_suppression(True)
        try:
            await asyncio.sleep(_CREDENTIALS_RECONNECT_INITIAL_DELAY)
            for attempt in range(_CREDENTIALS_RECONNECT_MAX_ATTEMPTS):
                if attempt:
                    await asyncio.sleep(_CREDENTIALS_RECONNECT_INTERVAL)
                try:
                    if await self.async_connect(block_error=True):
                        return True
                except AsusRouterAccessError as ex:
                    # Stale credentials are expected while httpd reloads
                    error = _access_error(ex)
                    if error is not ARAccessError.CREDENTIALS:
                        _LOGGER.error(
                            "Login on %s was changed, but the device refused "
                            "the new session (%s). The new credentials are "
                            "stored; check the device for a captcha or a "
                            "temporary login lock before reconnecting",
                            self._log_hostname,
                            error.name,
                        )
                        return False
                except AsusRouterError:
                    pass

            _LOGGER.error(
                "Login on %s was changed, but the new session could not be "
                "established in %s attempts. The new credentials are stored; "
                "reconnect manually if the device stays unreachable",
                self._log_hostname,
                _CREDENTIALS_RECONNECT_MAX_ATTEMPTS,
            )
            return False
        finally:
            self.set_error_suppression(prev_suppress)

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
            _LOGGER.debug(
                "Not connected to %s. Connecting...", self._log_hostname
            )
            await self.async_connect()

        if not self._connected:
            raise AsusRouterTimeoutError(
                "Connection timed out — could not establish initial connection"
            )

        _LOGGER.debug(
            "Sending `%s` request to `%s`", request_type, self._log_hostname
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
                f"Cannot connect to `{render_for_log(self._log_hostname)}` "
                f"on port `{self.port}`. Failed in `_send_request` with "
                f"error: `{ex}`"
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
                self._log_hostname,
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
            f"Cannot connect to `{render_for_log(self._log_hostname)}` "
            f"on port `{self.port}`. Failed in `_send_request` with "
            f"error: `{ex}`"
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

        if request_type == RequestType.POST and payload:
            # Some CGIs use a standard form parser and need the body verbatim;
            # re-quoting would corrupt the `=`/`&` separators
            payload_to_send = (
                payload
                if get_endpoint_raw_payload(endpoint)
                else quote(payload)
            )
        else:
            payload_to_send = None

        # Bound the live request: hold a permit for the whole exchange,
        # including reading the body (the connection stays in use until then)
        async with (
            self._request_semaphore,
            self._session.request(  # type: ignore[union-attr]
                request_type.value,
                url,
                data=payload_to_send,
                headers=headers,
                ssl=self.config.get(ARCCKey.VERIFY_SSL),
            ) as response,
        ):
            resp_status = response.status
            resp_headers = response.headers
            try:
                resp_content = await response.text()
            except UnicodeDecodeError:
                _LOGGER.debug("Cannot decode response. Will ignore errors")
                resp_content = await response.text(errors="ignore")

            if self._response_callback is not None:
                await self._response_callback(
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
                f"Fallback reconnect to "
                f"`{render_for_log(self._log_hostname)}` failed"
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
