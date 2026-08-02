"""Tests for the credentials validation."""

from __future__ import annotations

import pytest

from asusrouter.modules.credentials.validation import (
    CredentialsPolicy,
    validate_credentials,
)

# Fake credentials only - never a real login
_CUR_USER = "curuser"
_CUR_PASS = "curpass"

_STRICT = CredentialsPolicy(strict=True)
# A password that satisfies every strict rule (>=10, letter+digit+special,
# no consecutive identical characters)
_STRICT_OK = "Str0ng!pwd"


def _validate(**kwargs: object) -> str | None:
    """Validate with the fake current credentials and given overrides."""

    return validate_credentials(
        cur_username=_CUR_USER,
        cur_password=_CUR_PASS,
        new_username=kwargs.get("new_username"),  # type: ignore[arg-type]
        new_password=kwargs.get("new_password"),  # type: ignore[arg-type]
        policy=kwargs.get("policy", CredentialsPolicy()),  # type: ignore[arg-type]
    )


def test_accepts_valid_change() -> None:
    """A plain in-bounds change passes."""

    assert _validate(new_password="brandnewpass") is None


@pytest.mark.parametrize(
    ("new_username", "new_password"),
    [("", None), (None, "")],
    ids=["empty_username", "empty_password"],
)
def test_rejects_empty(
    new_username: str | None, new_password: str | None
) -> None:
    """An empty new value is rejected."""

    error = _validate(new_username=new_username, new_password=new_password)
    assert error is not None
    assert "must not be empty" in error


def test_rejects_too_long_username() -> None:
    """A username over the reported max is rejected."""

    policy = CredentialsPolicy(username_max=4)
    error = _validate(new_username="toolong", policy=policy)
    assert error == "username must be at most 4 characters"


def test_rejects_too_long_password() -> None:
    """A password over the reported max is rejected."""

    policy = CredentialsPolicy(password_max=4)
    error = _validate(new_password="toolong", policy=policy)
    assert error == "password must be at most 4 characters"


@pytest.mark.parametrize(
    "new_password",
    ["café", "пароль", "pass word", "emoji\U0001f512"],
    ids=["accent", "cyrillic", "nbsp", "emoji"],
)
def test_rejects_non_ascii_password(new_password: str) -> None:
    """A password the login payload cannot encode is refused up front."""

    error = _validate(new_password=new_password)
    assert error == "password must contain only ASCII characters"


@pytest.mark.parametrize(
    "new_username",
    ["good_name", "a1-b_2", "Router", "x"],
)
def test_accepts_valid_username(new_username: str) -> None:
    """Allowed login names pass the charset check."""

    assert _validate(new_username=new_username) is None


@pytest.mark.parametrize(
    "new_username",
    ["-lead", "_lead", "has space", "with!bang", "café", "trail\n"],
    ids=[
        "hyphen_first",
        "underscore_first",
        "space",
        "special",
        "non_ascii",
        "trailing_newline",
    ],
)
def test_rejects_bad_username_charset(new_username: str) -> None:
    """Disallowed characters or a leading hyphen/underscore are rejected."""

    error = _validate(new_username=new_username)
    assert error is not None
    assert "username may contain only" in error


def test_rejects_username_equal_password() -> None:
    """The resulting username and password must differ."""

    error = _validate(new_password=_CUR_USER)
    assert error == "username and password must not be the same"


def test_username_change_conflicts_with_current_password() -> None:
    """A new username equal to the current password is rejected."""

    error = _validate(new_username=_CUR_PASS)
    assert error == "username and password must not be the same"


def test_non_strict_allows_weak_password() -> None:
    """Without the strict policy, a simple password passes."""

    assert _validate(new_password="weak") is None


@pytest.mark.parametrize(
    ("password", "fragment"),
    [
        ("Sh0rt!", "at least 10"),
        ("1234567890!", "at least one letter"),
        ("abcdefghi!", "at least one number"),
        ("abcdefghi1", "at least one special character"),
        ("aabcdef1!x", "consecutive identical"),
    ],
)
def test_strict_password_rules(password: str, fragment: str) -> None:
    """Each strict rule rejects a password that violates only it."""

    error = _validate(new_password=password, policy=_STRICT)
    assert error is not None
    assert fragment in error


def test_strict_accepts_compliant_password() -> None:
    """A password meeting every strict rule passes."""

    assert _validate(new_password=_STRICT_OK, policy=_STRICT) is None
