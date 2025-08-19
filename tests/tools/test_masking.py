"""Tests for the masking tools."""

import hashlib
import hmac
import importlib
import sys
import threading
from types import ModuleType

import pytest

from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.masking import _read_key_from_string

MODULE = "asusrouter.tools.masking"
ENV_KEY_NAME = "ASUSROUTER_MASK_KEY"

TEST_KEY = "0f" * 32
TEST_MAC = "aa:bb:cc:11:22:33"


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


def test_configure_key_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test configuring key with bytes sets the exact key."""

    mod = _reload_masking(monkeypatch)

    # Set key
    key = b"13" * 32
    mod.configure_key(key)

    # Test that the key is set correctly
    assert mod.get_key_hex() == key.hex()


def test_configure_key_hex_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test configuring key with hex string sets the expected key."""

    mod = _reload_masking(monkeypatch)

    # Set key as hex string
    key_hex = "13" * 32
    mod.configure_key(key_hex)

    # Test that the key is set correctly
    assert mod.get_key_hex() == key_hex.lower()


def test_configure_key_any_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test configuring key with plain string uses UTF-8 encoding."""

    mod = _reload_masking(monkeypatch)

    # Set key as plain string
    s = "my-secret-key"
    mod.configure_key(s)

    # Test that the key is set correctly
    assert mod.get_key_hex() == s.encode().hex()


def test_configure_key_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test configuring key with None generates a new key."""

    mod = _reload_masking(monkeypatch)

    # Set a defined key
    mod.configure_key(b"\x00" * 32)
    k1 = mod.get_key_hex()

    # Set key to None
    mod.configure_key(None)
    k2 = mod.get_key_hex()

    # Test that the key is set
    assert isinstance(k2, str)

    # Test that the key is different
    assert k1 != k2


def test_configure_key_affects_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that configuring the key affects the output."""

    mod = _reload_masking(monkeypatch)

    mac = MacAddress.from_value(TEST_MAC)

    # Set key A
    mod.configure_key(b"A" * 32)
    m1 = mod.mask_mac(mac)

    # Set key B
    mod.configure_key(b"B" * 32)
    m2 = mod.mask_mac(mac)

    # Check that results are different
    assert m1 != m2

    # Set again key A and check that the result is the same as the first
    mod.configure_key(b"A" * 32)
    m1b = mod.mask_mac(mac)
    assert m1 == m1b


def test_masking_with_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test masking behavior with different environment configurations."""

    mod = _reload_masking(monkeypatch)

    orig = TEST_MAC
    m1 = mod.mask_mac(orig)
    m2 = mod.mask_mac(orig)

    assert isinstance(m1, MacAddress)
    assert isinstance(m2, MacAddress)

    # Check that masking is deterministic
    assert m1 == m2

    # Check that it differs from the original
    assert m1 != MacAddress.from_value(orig)


def test_masked_mac_locally_administered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that masked MAC is locally-administered."""

    mod = _reload_masking(monkeypatch)

    masked = mod.mask_mac(TEST_MAC)

    # Get the first byte
    b0 = masked.to_bytes()[0]

    # Locally-administered bit set
    assert (b0 & 0x02) != 0
    # Multicast bit cleared
    assert (b0 & 0x01) == 0


def test_mask_mac_invalid_input_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid MAC input should raise ValueError via MacAddress.from_value."""

    mod = _reload_masking(monkeypatch)

    with pytest.raises(ValueError, match="MAC"):
        mod.mask_mac("not-a-mac")


def test_configure_key_thread_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test concurrent configure_key + mask_mac behavior."""

    mod = _reload_masking(monkeypatch)

    # Writer changes the key repeatedly
    def writer(i: int) -> None:
        k = bytes([i % 256]) * 32
        for _ in range(50):
            mod.configure_key(k)

    # Reader calls mask_mac repeatedly and records success/failure
    results: list[bytes | tuple[str, str]] = []

    def reader() -> None:
        for _ in range(50):
            try:
                m = mod.mask_mac(TEST_MAC)
                results.append(m.to_bytes())
            except Exception as ex:  # noqa: BLE001
                results.append(("err", str(ex)))

    writers = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
    readers = [threading.Thread(target=reader) for _ in range(4)]

    for t in writers + readers:
        t.start()
    for t in writers + readers:
        t.join()

    # Ensure no reader observed exceptions
    assert all(not (isinstance(r, tuple) and r[0] == "err") for r in results)
    # And at least some successful reads happened
    assert len(results) > 0


def test_hmac_digest_thread_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    """_hmac_digest must produce the same result when invoked concurrently."""

    mod = _reload_masking(monkeypatch)

    key_bytes = bytes.fromhex(TEST_KEY)
    data = b"concurrent-payload"
    expected = hmac.new(key_bytes, data, hashlib.sha256).digest()

    threads_count = 16
    results: list[bytes | None] = [None] * threads_count

    def worker(idx: int) -> None:
        """Call the module-level helper without passing explicit key."""

        results[idx] = mod._hmac_digest(data, None)

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
    """Test _hmac_digest with a specific key."""

    mod = _reload_masking(monkeypatch)

    key = bytes.fromhex(TEST_KEY)
    data = b"payload"
    expected = hmac.new(key, data, hashlib.sha256).digest()

    result = mod._hmac_digest(data, key)
    assert result == expected
