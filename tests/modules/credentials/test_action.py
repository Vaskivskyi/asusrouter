"""Tests for the credentials action."""

from __future__ import annotations

from base64 import b64encode
from hashlib import md5
import logging
from unittest.mock import AsyncMock, Mock
from urllib.parse import parse_qs

import pytest

from asusrouter.const import AR_CALL_RUN_ACTION
from asusrouter.error import AsusRouterConnectionError
from asusrouter.modules.credentials.action import (
    ARCredentialsAction,
    run_action,
)
from asusrouter.modules.credentials.enums import ARCredentialsCapability
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.registry import ARCallableRegistry as ARCallReg

# Fake credentials only - never a real login
_CUR_USER = "curuser"
_CUR_PASS = "curpass"


def _md5(value: str) -> str:
    return md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()


def _b64(value: str) -> str:
    return b64encode(value.encode("utf-8")).decode("ascii")


def _getter() -> Mock:
    """Sync getter returning the current fake credentials."""

    return Mock(return_value=(_CUR_USER, _CUR_PASS))


def _poster(status: str | None = "200") -> AsyncMock:
    """Raw poster returning a chpass response with the given statusCode."""

    body = None if status is None else f'{{"statusCode":"{status}"}}'
    return AsyncMock(return_value=body)


def _sent_fields(
    poster: AsyncMock, endpoint: AREndpoint = AREndpoint.CHPASS
) -> dict[str, str]:
    """Parse the posted body into a field mapping, asserting the endpoint."""

    assert poster.await_args.kwargs["endpoint"] is endpoint
    body = poster.await_args.kwargs["request"]
    return {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}


def _identity(
    *,
    username_max: int = 32,
    password_max: int = 32,
    strict: bool = False,
    chpass: bool = True,
) -> Mock:
    """Identity advertising the given login capabilities, as translated."""

    capabilities: dict[ARCredentialsCapability, bool | int] = {}
    if username_max:
        capabilities[ARCredentialsCapability.USERNAME_MAX_LENGTH] = (
            username_max
        )
    if password_max:
        capabilities[ARCredentialsCapability.PASSWORD_MAX_LENGTH] = (
            password_max
        )
    if strict:
        capabilities[ARCredentialsCapability.SECURE_DEFAULT] = True
    if chpass:
        capabilities[ARCredentialsCapability.CHPASS] = True

    return Mock(support={ARSupportType.CREDENTIALS_CAPABILITIES: capabilities})


async def test_password_change_success() -> None:
    """A 200 response applies the change and resyncs stored credentials."""

    poster = _poster("200")
    setter = AsyncMock(return_value=True)

    result = await run_action(
        poster,
        ARCredentialsAction(new_password="freshpass"),
        credentials_get_callback=_getter(),
        credentials_set_callback=setter,
        fetch_raw_callback=poster,
        identity=_identity(),
    )

    assert result.success is True
    fields = _sent_fields(poster)
    assert fields["cur_username"] == _md5(_CUR_USER)
    assert fields["cur_passwd"] == _md5(_CUR_PASS)
    assert fields["new_passwd"] == _b64("freshpass")
    assert "new_username" not in fields
    # Password changed, username kept
    setter.assert_awaited_once_with(_CUR_USER, "freshpass")


async def test_username_change_success() -> None:
    """A username-only change keeps the current password on resync."""

    poster = _poster("200")
    setter = AsyncMock(return_value=True)

    result = await run_action(
        poster,
        ARCredentialsAction(new_username="freshuser"),
        credentials_get_callback=_getter(),
        credentials_set_callback=setter,
        fetch_raw_callback=poster,
        identity=_identity(),
    )

    assert result.success is True
    fields = _sent_fields(poster)
    assert fields["new_username"] == _b64("freshuser")
    assert "new_passwd" not in fields
    setter.assert_awaited_once_with("freshuser", _CUR_PASS)


async def test_both_change_success() -> None:
    """Changing both resyncs to both new values."""

    poster = _poster("200")
    setter = AsyncMock(return_value=True)

    result = await run_action(
        poster,
        ARCredentialsAction(
            new_username="freshuser", new_password="freshpass"
        ),
        credentials_get_callback=_getter(),
        credentials_set_callback=setter,
        fetch_raw_callback=poster,
        identity=_identity(),
    )

    assert result.success is True
    setter.assert_awaited_once_with("freshuser", "freshpass")


@pytest.mark.parametrize("status", ["401", "402", "999"])
async def test_failure_does_not_resync(status: str) -> None:
    """A non-success status reports failure and never swaps credentials."""

    poster = _poster(status)
    setter = AsyncMock()

    result = await run_action(
        poster,
        ARCredentialsAction(new_password="freshpass"),
        credentials_get_callback=_getter(),
        credentials_set_callback=setter,
        fetch_raw_callback=poster,
        identity=_identity(),
    )

    assert result.success is False
    setter.assert_not_awaited()


async def test_lost_response_does_not_resync() -> None:
    """A dropped response (None) is a failure; stored credentials stay put."""

    poster = _poster(None)
    setter = AsyncMock()

    result = await run_action(
        poster,
        ARCredentialsAction(new_password="freshpass"),
        credentials_get_callback=_getter(),
        credentials_set_callback=setter,
        fetch_raw_callback=poster,
    )

    assert result.success is False
    setter.assert_not_awaited()


async def test_connection_drop_reports_failure_without_swap() -> None:
    """A dropped connection on chpass fails without touching credentials."""

    poster = AsyncMock(side_effect=AsusRouterConnectionError("Server gone"))
    setter = AsyncMock()

    result = await run_action(
        poster,
        ARCredentialsAction(new_password="freshpass"),
        credentials_get_callback=_getter(),
        credentials_set_callback=setter,
        fetch_raw_callback=poster,
        identity=_identity(),
    )

    assert result.success is False
    setter.assert_not_awaited()


async def test_success_without_setter_callback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A missing set-callback reports success but warns about the session."""

    poster = _poster("200")

    with caplog.at_level(logging.WARNING):
        result = await run_action(
            poster,
            ARCredentialsAction(new_password="freshpass"),
            credentials_get_callback=_getter(),
            credentials_set_callback=None,
            fetch_raw_callback=poster,
            identity=_identity(),
        )

    assert result.success is True
    assert "not resynced" in caplog.text


async def test_no_getter_returns_failure() -> None:
    """Without a credentials getter, nothing is posted."""

    poster = _poster("200")

    result = await run_action(
        poster,
        ARCredentialsAction(new_password="freshpass"),
        credentials_get_callback=None,
        fetch_raw_callback=poster,
    )

    assert result.success is False
    poster.assert_not_awaited()


async def test_no_new_value_returns_failure() -> None:
    """An action with no new value never reaches the getter or the device."""

    poster = _poster("200")
    getter = _getter()

    result = await run_action(
        poster,
        ARCredentialsAction(),
        credentials_get_callback=getter,
        fetch_raw_callback=poster,
    )

    assert result.success is False
    getter.assert_not_called()
    poster.assert_not_awaited()


async def test_falls_back_to_primary_callback() -> None:
    """Without a raw callback, the primary callback posts the change."""

    primary = _poster("200")
    setter = AsyncMock(return_value=True)

    result = await run_action(
        primary,
        ARCredentialsAction(new_password="freshpass"),
        credentials_get_callback=_getter(),
        credentials_set_callback=setter,
        identity=_identity(),
    )

    assert result.success is True
    primary.assert_awaited_once()


async def test_rejects_change_over_max_length() -> None:
    """A value longer than the device max is rejected before sending."""

    poster = _poster("200")
    setter = AsyncMock()

    result = await run_action(
        poster,
        ARCredentialsAction(new_password="waytoolongpassword"),
        credentials_get_callback=_getter(),
        credentials_set_callback=setter,
        fetch_raw_callback=poster,
        identity=_identity(password_max=8),
    )

    assert result.success is False
    poster.assert_not_awaited()
    setter.assert_not_awaited()


async def test_rejects_username_equal_password(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A change making username equal password is rejected and warned."""

    poster = _poster("200")

    with caplog.at_level(logging.WARNING):
        result = await run_action(
            poster,
            ARCredentialsAction(new_password=_CUR_USER),
            credentials_get_callback=_getter(),
            fetch_raw_callback=poster,
            identity=_identity(),
        )

    assert result.success is False
    poster.assert_not_awaited()
    assert "rejected" in caplog.text


async def test_strict_policy_rejects_weak_password() -> None:
    """With secure_default set, a weak password is rejected."""

    poster = _poster("200")

    result = await run_action(
        poster,
        ARCredentialsAction(new_password="weak"),
        credentials_get_callback=_getter(),
        fetch_raw_callback=poster,
        identity=_identity(strict=True),
    )

    assert result.success is False
    poster.assert_not_awaited()


async def test_strict_policy_accepts_compliant_password() -> None:
    """A password meeting the strict rules is sent and applied."""

    poster = _poster("200")
    setter = AsyncMock(return_value=True)

    result = await run_action(
        poster,
        ARCredentialsAction(new_password="Str0ng!pwd"),
        credentials_get_callback=_getter(),
        credentials_set_callback=setter,
        fetch_raw_callback=poster,
        identity=_identity(strict=True),
    )

    assert result.success is True
    poster.assert_awaited_once()
    setter.assert_awaited_once_with(_CUR_USER, "Str0ng!pwd")


async def test_legacy_password_change() -> None:
    """Without chpass support, the change goes via start_apply.htm in plain."""

    poster = AsyncMock(return_value="<html>ok</html>")
    setter = AsyncMock(return_value=True)

    result = await run_action(
        poster,
        ARCredentialsAction(new_password="freshpass"),
        credentials_get_callback=_getter(),
        credentials_set_callback=setter,
        fetch_raw_callback=poster,
        identity=_identity(chpass=False),
    )

    assert result.success is True
    fields = _sent_fields(poster, AREndpoint.START_APPLY)
    assert fields["action_mode"] == "apply"
    # Username unchanged -> current; password plaintext, not hashed
    assert fields["http_username"] == _CUR_USER
    assert fields["http_passwd"] == "freshpass"
    assert fields["http_passwd2"] == "freshpass"
    assert fields["v_password2"] == "freshpass"
    setter.assert_awaited_once_with(_CUR_USER, "freshpass")


async def test_legacy_username_change() -> None:
    """A legacy username change sends the new name and current password."""

    poster = AsyncMock(return_value="<html>ok</html>")
    setter = AsyncMock(return_value=True)

    result = await run_action(
        poster,
        ARCredentialsAction(new_username="freshuser"),
        credentials_get_callback=_getter(),
        credentials_set_callback=setter,
        fetch_raw_callback=poster,
        identity=_identity(chpass=False),
    )

    assert result.success is True
    fields = _sent_fields(poster, AREndpoint.START_APPLY)
    assert fields["http_username"] == "freshuser"
    assert fields["http_passwd"] == _CUR_PASS
    setter.assert_awaited_once_with("freshuser", _CUR_PASS)


async def test_legacy_empty_response_fails() -> None:
    """An empty legacy response is treated as a failure."""

    poster = AsyncMock(return_value="")
    setter = AsyncMock()

    result = await run_action(
        poster,
        ARCredentialsAction(new_password="freshpass"),
        credentials_get_callback=_getter(),
        credentials_set_callback=setter,
        fetch_raw_callback=poster,
        identity=_identity(chpass=False),
    )

    assert result.success is False
    setter.assert_not_awaited()


async def test_no_identity_falls_back_to_legacy() -> None:
    """Without an identity, defaults apply and the legacy backend is used."""

    poster = AsyncMock(return_value="<html>ok</html>")

    result = await run_action(
        poster,
        ARCredentialsAction(new_password="freshpass"),
        credentials_get_callback=_getter(),
        credentials_set_callback=AsyncMock(return_value=True),
        fetch_raw_callback=poster,
    )

    assert result.success is True
    assert poster.await_args.kwargs["endpoint"] is AREndpoint.START_APPLY


async def test_non_dict_capabilities_falls_back_to_legacy() -> None:
    """A non-dict capabilities value yields defaults and the legacy backend."""

    poster = AsyncMock(return_value="<html>ok</html>")
    identity = Mock(support={ARSupportType.CREDENTIALS_CAPABILITIES: None})

    result = await run_action(
        poster,
        ARCredentialsAction(new_password="freshpass"),
        credentials_get_callback=_getter(),
        credentials_set_callback=AsyncMock(return_value=True),
        fetch_raw_callback=poster,
        identity=identity,
    )

    assert result.success is True
    assert poster.await_args.kwargs["endpoint"] is AREndpoint.START_APPLY


def test_action_is_registered() -> None:
    """The action is wired into the callable registry."""

    action = ARCredentialsAction(new_password="x")
    assert ARCallReg.get_callable(action, AR_CALL_RUN_ACTION) is not None


def test_action_repr_hides_secrets() -> None:
    """The action repr never exposes credential values."""

    action = ARCredentialsAction(new_username="secretuser", new_password="pw")
    assert "secretuser" not in repr(action)
    assert "pw" not in repr(action)
