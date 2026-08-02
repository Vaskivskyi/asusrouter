"""Supported login credentials."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.credentials.enums import ARCredentialsCapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.tools.converters.raw import raw_to_int
from asusrouter.tools.readers import is_true_in_dict

_CAPABILITY_FLAGS = {
    ARSupportValue.CHPASS.value: ARCredentialsCapability.CHPASS,
    ARSupportValue.SECURE_DEFAULT.value: (
        ARCredentialsCapability.SECURE_DEFAULT
    ),
}

_CAPABILITY_LENGTHS = {
    ARSupportValue.HTTP_PASSWORD_MAX_LENGTH.value: (
        ARCredentialsCapability.PASSWORD_MAX_LENGTH
    ),
    ARSupportValue.HTTP_USERNAME_MAX_LENGTH.value: (
        ARCredentialsCapability.USERNAME_MAX_LENGTH
    ),
}


def translate_credentials_capabilities(
    data: dict[str, Any],
) -> dict[ARCredentialsCapability, bool | int]:
    """Map advertised login capabilities; the MAX_LENGTHs carry ints."""

    capabilities: dict[ARCredentialsCapability, bool | int] = {
        capability: True
        for key, capability in _CAPABILITY_FLAGS.items()
        if is_true_in_dict(key, data)
    }
    for key, capability in _CAPABILITY_LENGTHS.items():
        # Unreported reads as 0 - leave it out so the caller uses its default
        length = raw_to_int(data.get(key))
        if length:
            capabilities[capability] = length

    return capabilities
