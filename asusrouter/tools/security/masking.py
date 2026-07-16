"""Deterministic masking engine.

Keyed HMAC-SHA256 backend used by identifier types to derive stable
pseudo-values from real ones. Operates on raw bytes only - the identifier
types own the conversion to and from their own representations.

This engine exists to avoid leaking sensitive information in logs and
during debugging. It does not guarantee that masked values are unique or
non-reversible and provides no security guarantees.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import threading

# Environment variable name for the mask key
_ENV_KEY_NAME = "ASUSROUTER_MASK_KEY"


def _read_key_from_string(key: str) -> bytes:
    """Read the key from a string."""

    # Try reading as hex
    try:
        return bytes.fromhex(key)
    # Fall back to encoding if hex conversion fails
    except ValueError:
        return key.encode()


# Try loading key from the environment variable
_key_env = os.environ.get(_ENV_KEY_NAME)
if _key_env is not None:
    _key = _read_key_from_string(_key_env)
# If there was no key to load, generate a new one for this runtime
else:
    _key = os.urandom(32)

# Lock to protect concurrent reads/writes of the module-level key
_key_lock = threading.RLock()


def configure_key(key: bytes | str | None) -> None:
    """Set the key used for deterministic masking."""

    global _key  # noqa: PLW0603

    # If it's a string, read it as bytes
    if isinstance(key, str):
        key = _read_key_from_string(key)

    # Write key under lock to avoid races with readers
    with _key_lock:
        if isinstance(key, bytes | bytearray):
            _key = bytes(key)
            return
        # Generate a new key
        _key = os.urandom(32)
        return


def hmac_digest(data: bytes, key: bytes | None = None) -> bytes:
    """Compute an HMAC-SHA256 digest of the data."""

    # `_key` is rebound atomically by configure_key, so reading it without
    # the lock always sees a whole key (never a torn value)
    k = key if key is not None else _key

    return hmac.new(k, data, hashlib.sha256).digest()


def get_key_hex() -> str:
    """Return current key as hex."""

    return _key.hex()
