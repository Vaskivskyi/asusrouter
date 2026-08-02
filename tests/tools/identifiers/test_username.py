"""Tests for username tools."""

from __future__ import annotations

import pytest

from asusrouter.tools.identifiers import Username
from asusrouter.tools.security import (
    REDACTED,
    REDACTED_STR,
    ARSecurityLevel,
    render,
)

_NAME = "fakeadmin"


class TestUsername:
    """Tests for the Username type."""

    def test_value(self) -> None:
        """The raw name is reachable only on purpose."""

        assert Username(_NAME).value == _NAME

    def test_string_redacts(self) -> None:
        """Formatting a username never spills it."""

        assert str(Username(_NAME)) == REDACTED_STR
        assert REDACTED_STR in repr(Username(_NAME))
        assert _NAME not in f"{Username(_NAME)!r}"

    def test_is_a_credential(self) -> None:
        """A login name is treated like the other half of the credential."""

        assert Username.reveal_level is ARSecurityLevel.UNSAFE
        assert Username.maskable is False

    @pytest.mark.parametrize(
        ("level", "revealed"),
        [
            (ARSecurityLevel.STRICT, False),
            (ARSecurityLevel.SANITIZED, False),
            (ARSecurityLevel.REASONABLE, False),
            (ARSecurityLevel.UNSAFE, True),
        ],
    )
    def test_render(self, level: ARSecurityLevel, revealed: bool) -> None:
        """The name is exposed only at the unsafe level."""

        rendered = render(Username(_NAME), level)

        assert (rendered is not REDACTED) is revealed

    def test_from_value(self) -> None:
        """An existing username is passed through, anything else wrapped."""

        username = Username(_NAME)

        assert Username.from_value(username) is username
        assert Username.from_value(_NAME) == username

    @pytest.mark.parametrize("value", [None, ""])
    def test_from_value_safe_empty(self, value: str | None) -> None:
        """A missing or empty name is no name at all."""

        assert Username.from_value_safe(value) is None

    def test_from_value_safe(self) -> None:
        """A real value is wrapped, an existing one passed through."""

        username = Username(_NAME)

        assert Username.from_value_safe(username) is username
        assert Username.from_value_safe(_NAME) == username

    def test_equality(self) -> None:
        """Usernames compare by value, including against a plain string."""

        assert Username(_NAME) == Username(_NAME)
        assert Username(_NAME) == _NAME
        assert Username(_NAME) != Username("other")
        assert Username(_NAME) != 42
        assert hash(Username(_NAME)) == hash(_NAME)
