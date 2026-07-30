"""Tests for text security tools."""

from __future__ import annotations

import pytest

from asusrouter.tools.identifiers import MacAddress, Serial, Username
from asusrouter.tools.security import (
    REDACTED,
    REDACTED_STR,
    ARSecurityLevel,
    render,
)
from asusrouter.tools.security.text import (
    SensitiveText,
    remove_secrets,
    searchable,
)

_TEXT = "pppd 2.4.7 started by fakeadmin, uid 0"


class TestSensitiveText:
    """Tests for the SensitiveText type."""

    def test_value(self) -> None:
        """The text is reachable only on purpose."""

        assert SensitiveText(_TEXT).value == _TEXT

    def test_string_redacts(self) -> None:
        """Formatting the text never spills it."""

        text = SensitiveText(_TEXT)

        assert str(text) == REDACTED_STR
        assert REDACTED_STR in repr(text)
        assert "pppd" not in repr(text)

    def test_defaults_to_unsafe(self) -> None:
        """Text nobody classified is closed by default."""

        assert SensitiveText(_TEXT).reveal_level is ARSecurityLevel.UNSAFE

    def test_never_masked(self) -> None:
        """Free text cannot be sanitized field by field, only withheld."""

        assert SensitiveText(_TEXT).maskable is False

    @pytest.mark.parametrize(
        ("reveal", "level", "revealed"),
        [
            (ARSecurityLevel.UNSAFE, ARSecurityLevel.REASONABLE, False),
            (ARSecurityLevel.UNSAFE, ARSecurityLevel.UNSAFE, True),
            (ARSecurityLevel.SANITIZED, ARSecurityLevel.REASONABLE, True),
            (ARSecurityLevel.SANITIZED, ARSecurityLevel.DEFAULT, False),
        ],
    )
    def test_render(
        self,
        reveal: ARSecurityLevel,
        level: ARSecurityLevel,
        revealed: bool,
    ) -> None:
        """The text is shown from its own level upwards, and not below."""

        rendered = render(SensitiveText(_TEXT, reveal), level)

        assert (rendered is not REDACTED) is revealed

    def test_equality(self) -> None:
        """Two texts match on both the value and the level."""

        strict = SensitiveText(_TEXT, ARSecurityLevel.STRICT)

        assert SensitiveText(_TEXT) == SensitiveText(_TEXT)
        assert SensitiveText(_TEXT) != strict
        assert SensitiveText(_TEXT) != _TEXT
        assert hash(SensitiveText(_TEXT)) == hash(SensitiveText(_TEXT))


class TestRemoveSecrets:
    """Tests for remove_secrets."""

    def test_removed_below_the_level(self) -> None:
        """A known secret is taken out of the text."""

        cleaned = remove_secrets(
            _TEXT, (Username("fakeadmin"),), ARSecurityLevel.REASONABLE
        )

        assert "fakeadmin" not in cleaned
        assert REDACTED_STR in cleaned
        assert cleaned.startswith("pppd 2.4.7 started by ")

    def test_kept_at_the_level(self) -> None:
        """At its own level the secret stays as the device wrote it."""

        assert (
            remove_secrets(
                _TEXT, (Username("fakeadmin"),), ARSecurityLevel.UNSAFE
            )
            == _TEXT
        )

    def test_every_occurrence(self) -> None:
        """A secret is removed wherever it appears, tag or message."""

        text = "fakeadmin: started by fakeadmin"

        cleaned = remove_secrets(
            text, (Username("fakeadmin"),), ARSecurityLevel.STRICT
        )

        assert "fakeadmin" not in cleaned

    def test_several_secrets(self) -> None:
        """Every given secret is considered, each at its own level."""

        text = "fakeadmin used AA:BB:CC:DD:EE:FF"
        secrets = (Username("fakeadmin"), MacAddress("AA:BB:CC:DD:EE:FF"))

        cleaned = remove_secrets(text, secrets, ARSecurityLevel.SANITIZED)

        # The name cannot be masked, so it goes; the MAC is below its
        # own reveal level here, so it is masked rather than removed
        assert "fakeadmin" not in cleaned
        assert "AA:BB:CC:DD:EE:FF" not in cleaned
        assert REDACTED_STR in cleaned

    def test_each_secret_at_its_own_level(self) -> None:
        """A level between two reveal levels touches only the lower one."""

        text = "fakeadmin used AA:BB:CC:DD:EE:FF"
        secrets = (Username("fakeadmin"), MacAddress("AA:BB:CC:DD:EE:FF"))

        cleaned = remove_secrets(text, secrets, ARSecurityLevel.REASONABLE)

        # A MAC is exposed at REASONABLE, a credential never is
        assert "aa:bb:cc:dd:ee:ff" in cleaned.lower()
        assert "fakeadmin" not in cleaned

    def test_nothing_to_remove(self) -> None:
        """Text without any of the secrets is untouched."""

        assert remove_secrets(_TEXT, (), ARSecurityLevel.STRICT) == _TEXT

    def test_valueless_secret(self) -> None:
        """A secret carrying no value cannot be searched for."""

        assert (
            remove_secrets(_TEXT, (Username(""),), ARSecurityLevel.STRICT)
            == _TEXT
        )

    def test_maskable_secret_keeps_correlation(self) -> None:
        """A secret that can be masked is replaced by its stand-in."""

        text = "fwver: x (sn:R2FAKE000000ABC)"

        cleaned = remove_secrets(
            text, (Serial("R2FAKE000000ABC"),), ARSecurityLevel.SANITIZED
        )

        assert "R2FAKE000000ABC" not in cleaned
        assert "sn:sn-" in cleaned

    def test_maskable_secret_redacted_below_sanitized(self) -> None:
        """Below the masking band even a maskable secret is withheld."""

        text = "fwver: x (sn:R2FAKE000000ABC)"

        cleaned = remove_secrets(
            text, (Serial("R2FAKE000000ABC"),), ARSecurityLevel.STRICT
        )

        assert REDACTED_STR in cleaned

    def test_case_insensitive(self) -> None:
        """A device spells one MAC both ways, so matching ignores case."""

        text = "up C8:1F:01:02:03:04 down c8:1f:01:02:03:04"

        cleaned = remove_secrets(
            text,
            (MacAddress("C8:1F:01:02:03:04"),),
            ARSecurityLevel.STRICT,
        )

        assert "01:02:03:04" not in cleaned.lower()

    def test_replacement_is_literal(self) -> None:
        """A replacement is inserted as text, never as a group reference."""

        cleaned = remove_secrets(
            "id AA:BB:CC:DD:EE:FF",
            (MacAddress("AA:BB:CC:DD:EE:FF"),),
            ARSecurityLevel.STRICT,
        )

        assert cleaned == f"id {REDACTED_STR}"


class TestSearchable:
    """Tests for searchable."""

    def test_credential_type(self) -> None:
        """A type redacting its string form hands the value over instead."""

        assert searchable(Username("fakeadmin")) == "fakeadmin"

    def test_identifier_type(self) -> None:
        """A type without `value` prints itself."""

        assert searchable(MacAddress("AA:BB:CC:DD:EE:FF")) == (
            "aa:bb:cc:dd:ee:ff"
        )

    def test_nothing_to_search_for(self) -> None:
        """A value that redacts and hides itself cannot be searched for."""

        assert searchable(Username("")) is None
