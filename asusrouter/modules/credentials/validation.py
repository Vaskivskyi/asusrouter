"""Credential validation for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass
import re
import string

# Fallback max length when the device does not report MaxLen_http_*
DEFAULT_MAX_LENGTH = 32

# Allowed login name: letters/digits, then also hyphen/underscore, but the
# first character may not be a hyphen or underscore. Matched with fullmatch
# so a trailing newline cannot slip through the `$` anchor
_USERNAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")

# Strict (secure_default) password policy
_MIN_STRICT_PASSWORD_LENGTH = 10
_SPECIAL_CHARS = frozenset(string.punctuation)


@dataclass(frozen=True)
class CredentialsPolicy:
    """Device rules a credential change must satisfy."""

    username_max: int = DEFAULT_MAX_LENGTH
    password_max: int = DEFAULT_MAX_LENGTH
    strict: bool = False


def _has_consecutive_identical(value: str) -> bool:
    """Whether the value has two identical characters in a row."""

    return any(a == b for a, b in zip(value, value[1:]))


def _validate_length(value: str, maximum: int, label: str) -> str | None:
    """Check a value is non-empty and within the max length."""

    if not value:
        return f"{label} must not be empty"
    if len(value) > maximum:
        return f"{label} must be at most {maximum} characters"
    return None


def _validate_strict_password(password: str) -> str | None:
    """Apply the secure-default password rules; return an error or None."""

    if len(password) < _MIN_STRICT_PASSWORD_LENGTH:
        return (
            f"password must be at least {_MIN_STRICT_PASSWORD_LENGTH} "
            "characters"
        )
    if not any(char.isalpha() for char in password):
        return "password must contain at least one letter"
    if not any(char.isdigit() for char in password):
        return "password must contain at least one number"
    if not any(char in _SPECIAL_CHARS for char in password):
        return "password must contain at least one special character"
    if _has_consecutive_identical(password):
        return "password must not contain consecutive identical characters"
    return None


def _validate_username(username: str, policy: CredentialsPolicy) -> str | None:
    """Check a new login name's length and character set."""

    error = _validate_length(username, policy.username_max, "username")
    if error:
        return error
    if not _USERNAME_RE.fullmatch(username):
        return (
            "username may contain only letters, digits, hyphens and "
            "underscores, and may not start with a hyphen or underscore"
        )
    return None


def _validate_password(password: str, policy: CredentialsPolicy) -> str | None:
    """Check a new password's length and, when strict, its complexity."""

    error = _validate_length(password, policy.password_max, "password")
    if error:
        return error
    # The login payload is ASCII-encoded
    if not password.isascii():
        return "password must contain only ASCII characters"
    if policy.strict:
        return _validate_strict_password(password)
    return None


def validate_credentials(
    *,
    cur_username: str,
    cur_password: str,
    new_username: str | None,
    new_password: str | None,
    policy: CredentialsPolicy = CredentialsPolicy(),
) -> str | None:
    """Check a credential change against known device rules.

    Returns a human-readable error string for the first failed rule, or None
    when the change should be accepted. Length limits and the username/password
    match are universal; the strict complexity rules apply only when the device
    reports the secure-default policy.
    """

    if new_username is not None and (
        error := _validate_username(new_username, policy)
    ):
        return error

    if new_password is not None and (
        error := _validate_password(new_password, policy)
    ):
        return error

    # The resulting login name and password must differ
    final_username = cur_username if new_username is None else new_username
    final_password = cur_password if new_password is None else new_password
    if final_username == final_password:
        return "username and password must not be the same"

    return None


__all__ = [
    "DEFAULT_MAX_LENGTH",
    "CredentialsPolicy",
    "validate_credentials",
]
