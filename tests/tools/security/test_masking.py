"""Tests for the masking engine."""

from __future__ import annotations

import hashlib
import hmac
import importlib
import sys
import threading
from types import ModuleType

import pytest

from asusrouter.tools.security.masking import _read_key_from_string

MODULE = "asusrouter.tools.security.masking"
ENV_KEY_NAME = "ASUSROUTER_MASK_KEY"

TEST_KEY = "0f" * 32


def _reload_masking_with_env(
    monkeypatch: pytest.MonkeyPatch, env_value: str
) -> ModuleType:
    """Set up environment for testing masking."""

    monkeypatch.setenv(ENV_KEY_NAME, env_value)

    # remove possibly cached module so env var is read at import time
    sys.modules.pop(MODULE, None)
    return importlib.import_module(MODULE)


def _reload_masking(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Reload the masking module without any environment variables."""

    return _reload_masking_with_env(monkeypatch, TEST_KEY)


@pytest.mark.parametrize(
    ("key_str", "key"),
    [
        # even-length valid hex (lowercase)
        ("0f" * 32, bytes.fromhex("0f" * 32)),
        # even-length valid hex (uppercase)
        ("0F" * 32, bytes.fromhex("0F" * 32)),
        # empty string -> fromhex('') -> b''
        ("", bytes.fromhex("")),
        # plain non-hex string -> fallback to UTF-8 encoding
        ("my-secret-key", b"my-secret-key"),
        # invalid-hex characters (even length) -> fallback to encoding
        ("zz" * 16, ("zz" * 16).encode()),
        # odd-length string -> fromhex would raise -> fallback to encoding
        ("abc", b"abc"),
    ],
)
def test_read_key_from_string(key_str: str, key: bytes) -> None:
    """Test _read_key_from_string method."""

    assert _read_key_from_string(key_str) == key


@pytest.mark.parametrize("key", [TEST_KEY, "1234567890"])
def test_env_load(key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test if environment variables are loaded correctly."""

    # Set environment variable
    mod = _reload_masking_with_env(monkeypatch, key)

    # Check via the public API call
    assert mod.get_key_hex().lower() == key.lower()
    assert bytes.fromhex(mod.get_key_hex()) == bytes.fromhex(key)


def test_configure_key_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test configuring key with bytes sets the exact key."""

    mod = _reload_masking(monkeypatch)

    key = b"13" * 32
    mod.configure_key(key)

    assert mod.get_key_hex() == key.hex()


def test_configure_key_hex_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test configuring key with hex string sets the expected key."""

    mod = _reload_masking(monkeypatch)

    key_hex = "13" * 32
    mod.configure_key(key_hex)

    assert mod.get_key_hex() == key_hex.lower()


def test_configure_key_any_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test configuring key with plain string uses UTF-8 encoding."""

    mod = _reload_masking(monkeypatch)

    s = "my-secret-key"
    mod.configure_key(s)

    assert mod.get_key_hex() == s.encode().hex()


def test_configure_key_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test configuring key with None generates a new key."""

    mod = _reload_masking(monkeypatch)

    mod.configure_key(b"\x00" * 32)
    k1 = mod.get_key_hex()

    mod.configure_key(None)
    k2 = mod.get_key_hex()

    assert isinstance(k2, str)
    assert k1 != k2


def test_configure_key_affects_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that configuring the key affects the digest."""

    mod = _reload_masking(monkeypatch)

    data = b"payload"

    mod.configure_key(b"A" * 32)
    d1 = mod.hmac_digest(data)

    mod.configure_key(b"B" * 32)
    d2 = mod.hmac_digest(data)

    assert d1 != d2

    # Same key -> same digest (deterministic)
    mod.configure_key(b"A" * 32)
    assert mod.hmac_digest(data) == d1


def test_hmac_digest_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    """The digest must be deterministic for the same input and key."""

    mod = _reload_masking(monkeypatch)

    data = b"payload"
    assert mod.hmac_digest(data) == mod.hmac_digest(data)


def test_hmac_digest_thread_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    """hmac_digest must produce the same result when invoked concurrently."""

    mod = _reload_masking(monkeypatch)

    key_bytes = bytes.fromhex(TEST_KEY)
    data = b"concurrent-payload"
    expected = hmac.new(key_bytes, data, hashlib.sha256).digest()

    threads_count = 16
    results: list[bytes | None] = [None] * threads_count

    def worker(idx: int) -> None:
        """Call the module-level helper without passing explicit key."""

        results[idx] = mod.hmac_digest(data, None)

    threads = [
        threading.Thread(target=worker, args=(i,))
        for i in range(threads_count)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(r == expected for r in results)


def test_hmac_digest_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test hmac_digest with a specific key."""

    mod = _reload_masking(monkeypatch)

    key = bytes.fromhex(TEST_KEY)
    data = b"payload"
    expected = hmac.new(key, data, hashlib.sha256).digest()

    assert mod.hmac_digest(data, key) == expected


def test_configure_key_thread_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test concurrent configure_key + hmac_digest behavior."""

    mod = _reload_masking(monkeypatch)

    def writer(i: int) -> None:
        k = bytes([i % 256]) * 32
        for _ in range(50):
            mod.configure_key(k)

    results: list[bytes | tuple[str, str]] = []

    def reader() -> None:
        for _ in range(50):
            try:
                results.append(mod.hmac_digest(b"payload"))
            except Exception as ex:  # noqa: BLE001
                results.append(("err", str(ex)))

    writers = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
    readers = [threading.Thread(target=reader) for _ in range(4)]

    for t in writers + readers:
        t.start()
    for t in writers + readers:
        t.join()

    assert all(not (isinstance(r, tuple) and r[0] == "err") for r in results)
    assert len(results) > 0
