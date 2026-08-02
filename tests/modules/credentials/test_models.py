"""Tests for the credentials data models."""

from __future__ import annotations

from base64 import b64encode
from hashlib import md5
from typing import Any
from urllib.parse import parse_qs

import pytest

from asusrouter.modules.credentials.enums import ARCredentialsStatus
from asusrouter.modules.credentials.models import (
    build_chpass_request,
    read_chpass_result,
)

# Fake credentials only - never a real login
_CUR_USER = "curuser"
_CUR_PASS = "curpass"


def _md5(value: str) -> str:
    """Independent reference digest for the current-credential fields."""

    return md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()


def _b64(value: str) -> str:
    """Independent reference base64 for the new-credential field."""

    return b64encode(value.encode("utf-8")).decode("ascii")


def _fields(body: str) -> dict[str, str]:
    """Parse the request body into a single-value field mapping."""

    return {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}


def test_build_username_change() -> None:
    """A username change carries the current creds plus the base64 name."""

    body = build_chpass_request(_CUR_USER, _CUR_PASS, new_username="brandnew")
    fields = _fields(body)

    assert fields["cur_username"] == _md5(_CUR_USER)
    assert fields["cur_passwd"] == _md5(_CUR_PASS)
    assert fields["new_username"] == _b64("brandnew")
    assert fields["restart_httpd"] == "1"
    assert "new_passwd" not in fields


def test_build_password_change() -> None:
    """A password change carries the current creds plus the base64 password."""

    # Padding '=' in the base64 must survive the url-encoding round trip
    body = build_chpass_request(
        _CUR_USER, _CUR_PASS, new_password="s3cr3t/p+w"
    )
    fields = _fields(body)

    assert fields["cur_username"] == _md5(_CUR_USER)
    assert fields["cur_passwd"] == _md5(_CUR_PASS)
    assert fields["new_passwd"] == _b64("s3cr3t/p+w")
    assert fields["restart_httpd"] == "1"
    assert "new_username" not in fields


def test_build_special_chars_are_quoted() -> None:
    """Base64 `+` / `/` are percent-encoded, not left as separators."""

    body = build_chpass_request(_CUR_USER, _CUR_PASS, new_password="ûÿ")
    expected = _b64("ûÿ")

    # The raw base64 (with + or /) must not appear verbatim in the body
    assert expected not in body
    assert _fields(body)["new_passwd"] == expected


def test_build_both_change() -> None:
    """Username and password can change together in one request."""

    body = build_chpass_request(
        _CUR_USER, _CUR_PASS, new_username="brandnew", new_password="s3cret"
    )
    fields = _fields(body)

    assert fields["new_username"] == _b64("brandnew")
    assert fields["new_passwd"] == _b64("s3cret")
    assert fields["cur_username"] == _md5(_CUR_USER)
    assert fields["cur_passwd"] == _md5(_CUR_PASS)


def test_build_requires_at_least_one_new_value() -> None:
    """Providing no new value is a misuse and raises."""

    with pytest.raises(ValueError, match="at least one"):
        build_chpass_request(_CUR_USER, _CUR_PASS)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"statusCode":"200"}', ARCredentialsStatus.SUCCESS),
        ('{"statusCode":"401"}', ARCredentialsStatus.WRONG_PASSWORD),
        ({"statusCode": "402"}, ARCredentialsStatus.LOCKED_OUT),
        ('{"statusCode":"999"}', ARCredentialsStatus.UNKNOWN),
        ("{}", ARCredentialsStatus.UNKNOWN),
        ("not json", ARCredentialsStatus.UNKNOWN),
        ("[1, 2, 3]", ARCredentialsStatus.UNKNOWN),
        (None, ARCredentialsStatus.UNKNOWN),
        (42, ARCredentialsStatus.UNKNOWN),
    ],
)
def test_read_chpass_result(raw: Any, expected: ARCredentialsStatus) -> None:
    """The response parses into the matching status, else UNKNOWN."""

    assert read_chpass_result(raw) is expected
