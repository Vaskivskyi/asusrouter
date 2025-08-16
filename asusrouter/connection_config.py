"""Connection configuration module.

This module handles the configuration of the connection settings
for the library.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from asusrouter.config import (
    CONFIG_DEFAULT_ALREADY_NOTIFIED,
    CONFIG_DEFAULT_BOOL,
    CONFIG_DEFAULT_INT,
    ARConfigBase,
    ARConfigKeyBase,
    safe_bool_config,
    safe_int_config,
)


class ARConnectionConfigKey(ARConfigKeyBase):
    """Connection configuration keys for AsusRouter."""

    # Allow automatic fallback
    ALLOW_FALLBACK = "allow_fallback"
    # Allow multiple fallbacks
    ALLOW_MULTIPLE_FALLBACKS = "allow_multiple_fallbacks"
    # Allow upgrade from HTTP to HTTPS
    ALLOW_UPGRADE_HTTP_TO_HTTPS = "allow_upgrade_http_to_https"
    # Port
    PORT = "port"
    # Strict SSL
    STRICT_SSL = "strict_ssl"
    NOTIFIED_STRICT_SSL_NO_SSL = "notified_strict_ssl_fallback"
    # Use SSL
    USE_SSL = "use_ssl"
    # Verify SSL certificate
    VERIFY_SSL = "verify_ssl"
    NOTIFIED_VERIFY_SSL_FAILED = "notified_verify_ssl_failed"


CONNECTION_CONFIG_DEFAULT: dict[ARConnectionConfigKey, Any] = {
    # Allow automatic fallback
    ARConnectionConfigKey.ALLOW_FALLBACK: CONFIG_DEFAULT_BOOL,
    # Allow multiple fallbacks
    # If set, AsusRouter will allow fallback to a different connection method
    # any number of times
    # (except for consecutive attempts, where loop protection will trigger)
    ARConnectionConfigKey.ALLOW_MULTIPLE_FALLBACKS: CONFIG_DEFAULT_BOOL,
    # Allow upgrade from HTTP to HTTPS
    ARConnectionConfigKey.ALLOW_UPGRADE_HTTP_TO_HTTPS: True,
    # Port
    ARConnectionConfigKey.PORT: CONFIG_DEFAULT_INT,
    # If set, AsusRouter will not allow falling back to a non-SSL connection
    # automatically.
    ARConnectionConfigKey.STRICT_SSL: CONFIG_DEFAULT_BOOL,
    ARConnectionConfigKey.NOTIFIED_STRICT_SSL_NO_SSL: CONFIG_DEFAULT_ALREADY_NOTIFIED,  # noqa: E501
    # Use SSL
    ARConnectionConfigKey.USE_SSL: CONFIG_DEFAULT_BOOL,
    # If set, AsusRouter will verify SSL certificates when connecting
    # via HTTPS. Most Asus routers use self-signed certificates, so
    # connections may fail unless you manually add the issuer to your
    # trusted certificates.
    ARConnectionConfigKey.VERIFY_SSL: CONFIG_DEFAULT_BOOL,
    ARConnectionConfigKey.NOTIFIED_VERIFY_SSL_FAILED: CONFIG_DEFAULT_ALREADY_NOTIFIED,  # noqa: E501
}

CONNECTION_CONFIG_TYPES_DEFAULTS: dict[
    ARConnectionConfigKey, Callable[[Any], Any]
] = {
    # Allow automatic fallback
    ARConnectionConfigKey.ALLOW_FALLBACK: safe_bool_config,
    # Allow multiple fallbacks
    ARConnectionConfigKey.ALLOW_MULTIPLE_FALLBACKS: safe_bool_config,
    # Allow upgrade from HTTP to HTTPS
    ARConnectionConfigKey.ALLOW_UPGRADE_HTTP_TO_HTTPS: safe_bool_config,
    # Port
    ARConnectionConfigKey.PORT: safe_int_config,
    # Strict SSL
    ARConnectionConfigKey.STRICT_SSL: safe_bool_config,
    ARConnectionConfigKey.NOTIFIED_STRICT_SSL_NO_SSL: safe_bool_config,
    # Use SSL
    ARConnectionConfigKey.USE_SSL: safe_bool_config,
    # Verify SSL certificate
    ARConnectionConfigKey.VERIFY_SSL: safe_bool_config,
    ARConnectionConfigKey.NOTIFIED_VERIFY_SSL_FAILED: safe_bool_config,
}


class ARConnectionConfig(ARConfigBase):
    """Connection configuration for AsusRouter."""

    def __init__(
        self,
        defaults: dict[ARConnectionConfigKey, Any] | None = None,
    ) -> None:
        """Initialize the connection configuration."""

        super().__init__()
        self.reset(defaults)

    def reset(
        self,
        defaults: dict[ARConnectionConfigKey, Any] | None = None,
    ) -> None:
        """Reset all connection configuration options."""

        super().reset()

        with self._lock:
            defaults = defaults or CONNECTION_CONFIG_DEFAULT
            for key in ARConnectionConfigKey:
                self._options[key] = defaults.get(key)
                self._types[key] = CONNECTION_CONFIG_TYPES_DEFAULTS.get(
                    key, safe_bool_config
                )
