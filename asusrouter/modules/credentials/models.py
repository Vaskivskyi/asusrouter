"""Credentials data models for AsusRouter."""

from __future__ import annotations

from base64 import b64encode
from hashlib import md5
import json
from typing import Any

from asusrouter.const import RequestType
from asusrouter.modules.common.command import ARService
from asusrouter.modules.common.status import STATUS_CODE_KEY
from asusrouter.modules.credentials.enums import ARCredentialsStatus
from asusrouter.tools.writers import dict_to_request


def _md5_hex(value: str) -> str:
    """Return the lowercase MD5 hex digest the WebUI sends for creds."""

    # Not a security hash; the wire protocol expects this digest
    return md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()


def _b64(value: str) -> str:
    """Return the base64 form the WebUI sends for new credential values."""

    return b64encode(value.encode("utf-8")).decode("ascii")


def build_chpass_request(
    cur_username: str,
    cur_password: str,
    *,
    new_username: str | None = None,
    new_password: str | None = None,
) -> str:
    """Build the CHPASS request body for a credential change."""

    if new_username is None and new_password is None:
        raise ValueError(
            "at least one of new_username or new_password is required"
        )

    data: dict[str, Any] = {
        "cur_username": _md5_hex(cur_username),
        "cur_passwd": _md5_hex(cur_password),
        ARService.WEBUI_RESTART.value: "1",
    }
    if new_username is not None:
        data["new_username"] = _b64(new_username)
    if new_password is not None:
        data["new_passwd"] = _b64(new_password)

    return dict_to_request(data, request_type=RequestType.GET)


def read_chpass_result(raw: Any) -> ARCredentialsStatus:
    """Read the CHPASS response into a status."""

    data: Any = raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return ARCredentialsStatus.UNKNOWN
    if not isinstance(data, dict):
        return ARCredentialsStatus.UNKNOWN
    return ARCredentialsStatus.from_value(data.get(STATUS_CODE_KEY))


__all__ = [
    "build_chpass_request",
    "read_chpass_result",
]
