"""Credentials action for AsusRouter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from asusrouter.error import AsusRouterConnectionError, AsusRouterTimeoutError
from asusrouter.modules.action import ARAction
from asusrouter.modules.credentials.enums import ARCredentialsStatus
from asusrouter.modules.credentials.legacy import build_legacy_request
from asusrouter.modules.credentials.models import (
    build_chpass_request,
    read_chpass_result,
)
from asusrouter.modules.credentials.validation import (
    DEFAULT_MAX_LENGTH,
    CredentialsPolicy,
    validate_credentials,
)
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.service.action import ARServiceResult
from asusrouter.modules.support import (
    ARSupportSourceUniversal,
    support_available,
    support_value,
)
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.types import ARCallbackType

_LOGGER = logging.getLogger(__name__)


# repr=False keeps ARAction's field-free repr, so credential values never
# reach logs; eq=False keeps type-only equality (no secrets in the hash key)
@dataclass(eq=False, repr=False, kw_only=True)
class ARCredentialsAction(ARAction):
    """Change the router login username and/or password."""

    new_username: str | None = None
    new_password: str | None = None


async def _fetch_support(
    fetch_data_callback: ARCallbackType | None,
) -> dict[ARSupportType, Any]:
    """Fetch the device support flags, or an empty map when unavailable."""

    if fetch_data_callback is None:
        return {}
    fetched = await fetch_data_callback(ARSupportSourceUniversal)
    if isinstance(fetched, dict):
        return fetched.get(ARSupportSourceUniversal) or {}
    return {}


def _policy_from_support(
    support: dict[ARSupportType, Any],
) -> CredentialsPolicy:
    """Derive the credential rules from the support flags."""

    return CredentialsPolicy(
        username_max=(
            support_value(support, ARSupportType.HTTP_USERNAME_MAX_LENGTH)
            or DEFAULT_MAX_LENGTH
        ),
        password_max=(
            support_value(support, ARSupportType.HTTP_PASSWORD_MAX_LENGTH)
            or DEFAULT_MAX_LENGTH
        ),
        strict=support_available(support, ARSupportType.SECURE_DEFAULT),
    )


def _change_accepted(use_chpass: bool, raw: Any) -> bool:
    """Whether the device accepted the change, per backend."""

    if not use_chpass:
        # Should return its page on success; empty/None means failure
        if not raw:
            _LOGGER.warning("Login change failed: no response from the device")
            return False
        return True

    status = read_chpass_result(raw)
    if status is ARCredentialsStatus.SUCCESS:
        return True
    if status is ARCredentialsStatus.WRONG_PASSWORD:
        _LOGGER.warning("Login change rejected: wrong current password")
    elif status is ARCredentialsStatus.LOCKED_OUT:
        _LOGGER.warning("Login change blocked: too many failed attempts")
    else:
        _LOGGER.debug("Login change failed: %s", status)
    return False


async def run_action(
    callback: ARCallbackType,
    action: ARCredentialsAction,
    *,
    credentials_get_callback: Callable[[], tuple[str, str]] | None = None,
    credentials_set_callback: ARCallbackType | None = None,
    fetch_raw_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> ARServiceResult:
    """Change the router login username/password."""

    if credentials_get_callback is None:
        _LOGGER.debug("No credentials getter available; cannot change login")
        return ARServiceResult(success=False)

    if action.new_username is None and action.new_password is None:
        _LOGGER.debug("No new credential value provided; nothing to change")
        return ARServiceResult(success=False)

    cur_username, cur_password = credentials_get_callback()
    # The credentials the session will use once the change lands
    new_username = action.new_username or cur_username
    new_password = action.new_password or cur_password

    # Reject changes the device is known to refuse, before sending them
    support = await _fetch_support(kwargs.get("fetch_data_callback"))
    error = validate_credentials(
        cur_username=cur_username,
        cur_password=cur_password,
        new_username=action.new_username,
        new_password=action.new_password,
        policy=_policy_from_support(support),
    )
    if error is not None:
        _LOGGER.warning("Login change rejected: %s", error)
        return ARServiceResult(success=False)

    use_chpass = support_available(support, ARSupportType.CHPASS)
    # New FW
    if use_chpass:
        endpoint = AREndpoint.CHPASS
        request = build_chpass_request(
            cur_username,
            cur_password,
            new_username=action.new_username,
            new_password=action.new_password,
        )
    # Legacy
    else:
        endpoint = AREndpoint.START_APPLY
        request = build_legacy_request(new_username, new_password)

    poster = fetch_raw_callback or callback
    try:
        raw = await poster(endpoint=endpoint, request=request)
    except (AsusRouterConnectionError, AsusRouterTimeoutError) as ex:
        _LOGGER.warning("Login change could not be confirmed: %s", ex)
        return ARServiceResult(success=False)

    if not _change_accepted(use_chpass, raw):
        return ARServiceResult(success=False)

    # Apply new credentials to our connection
    if credentials_set_callback is not None:
        await credentials_set_callback(new_username, new_password)
    else:
        _LOGGER.warning(
            "Login changed on the device but the session was not resynced; "
            "reconnect with the new credentials"
        )

    return ARServiceResult(success=True)


ARCallReg.register_action(ARCredentialsAction, run_action=run_action)


__all__ = [
    "ARCredentialsAction",
    "run_action",
]
