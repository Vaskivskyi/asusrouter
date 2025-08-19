"""Masking tools.

This module provides functions for masking sensitive data
(e.g. MAC addresses) using a deterministic masking approach.

This module exists to avoid leaking sensitive information in logs
and during debugging. At the same time, it does not guarantee
that the masked values are unique or non-reversible.

This module does not provide any security guarantees.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import threading

from asusrouter.tools.identifiers import MacAddress

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


def _hmac_digest(data: bytes, key: bytes | None = None) -> bytes:
    """Compute HMAC-SHA256 digest."""

    # Use the provided key or the loaded mask key
    if key is not None:
        k = key
    else:
        # Read the module key under lock to ensure a consistent view
        with _key_lock:
            k = _key

    return hmac.new(k, data, hashlib.sha256).digest()


def mask_mac(
    real_mac: MacAddress | str | bytes | bytearray | int,
    key: bytes | None = None,
) -> MacAddress:
    """Deterministically map real MAC -> pseudo-MAC.

    - Uses HMAC-SHA256(key, real_mac) and takes the first 6 bytes.
    - Creates a new MacAddress instance from the masked bytes.
    - Sets it to a locally-administered MAC address.
    - Returns the masked MacAddress instance.
    """

    # Make sure we have a MacAddress. If we get a wrong input,
    # it will automatically raise a ValueError
    mac_obj = MacAddress.from_value(real_mac)

    # Compute the HMAC digest
    digest = _hmac_digest(mac_obj.to_bytes(), key)

    # Use first 6 bytes to create masked MAC
    masked_mac = MacAddress(digest[:6])

    # Set masked MAC as locally-administered
    masked_mac.set_locally_administered()

    return masked_mac


def get_key_hex() -> str:
    """Return current key as hex."""

    return _key.hex()
