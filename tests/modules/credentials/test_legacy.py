"""Tests for the legacy credential change."""

from __future__ import annotations

from urllib.parse import parse_qs

from asusrouter.modules.credentials.legacy import build_legacy_request


def _fields(body: str) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}


def test_build_legacy_request() -> None:
    """The body carries plaintext credentials and the apply fields."""

    fields = _fields(build_legacy_request("someuser", "s3cret/p+w"))

    assert fields["action_mode"] == "apply"
    assert fields["action_script"] == "restart_time;restart_upnp;"
    assert fields["http_username"] == "someuser"
    # Plaintext (url-encoding round-trips), not hashed or base64
    assert fields["http_passwd"] == "s3cret/p+w"
    assert fields["http_passwd2"] == "s3cret/p+w"
    assert fields["v_password2"] == "s3cret/p+w"
