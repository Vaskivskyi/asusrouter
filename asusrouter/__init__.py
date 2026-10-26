"""Initialize AsusRouter."""

from __future__ import annotations

from .asusrouter import AsusRouter
from .error import AsusRouterError
from .modules.static_dhcp import StaticDHCPLease
from .tools.security.log import install_log_masking

# Mask sensitive values in log records emitted by this package
install_log_masking()

__all__ = [
    "AsusRouter",
    "AsusRouterError",
    "StaticDHCPLease",
]
