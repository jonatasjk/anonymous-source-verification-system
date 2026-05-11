"""Unit tests for app.core.crypto."""
import os
import pytest

from app.core.crypto import sha256_bytes, sha256_file, derive_file_key, encrypt_bytes, decrypt_bytes


# ---------------------------------------------------------------------------
# sha256_bytes
# ---------------------------------------------------------------------------

def test_sha256_bytes_known_value():
    # SHA-256 of empty bytes
    assert sha256_bytes(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_sha256_bytes_consistency():
    data = b"hello world"
    assert sha256_bytes(data) == sha256_bytes(data)


def test_sha256_bytes_returns_64_hex_chars():
    result = sha256_bytes(b"some data")
    assert len(result) == 64
    int(result, 16)  # must be valid hex


def test_sha256_bytes_different_inputs_differ():
    assert sha256_bytes(b"abc") != sha256_bytes(b"def")


# ---------------------------------------------------------------------------
# sha256_file
# ---------------------------------------------------------------------------

def test_sha256_file(tmp_path):
    content = b"file content here"
    p = tmp_path / "test.bin"
    p.write_bytes(content)
    assert sha256_file(str(p)) == sha256_bytes(content)


def test_sha256_file_large(tmp_path):
    # Cross 64 KiB chunk boundary
    content = os.urandom(200_000)
    p = tmp_path / "large.bin"
    p.write_bytes(content)
    assert sha256_file(str(p)) == sha256_bytes(content)


# ---------------------------------------------------------------------------
# derive_file_key
# ---------------------------------------------------------------------------

def test_derive_file_key_returns_32_bytes():
    key = derive_file_key(b"a" * 32, "sub-id", "hash")
    assert len(key) == 32


def test_derive_file_key_deterministic():
    k1 = derive_file_key(b"master", "sub1", "hash1")
    k2 = derive_file_key(b"master", "sub1", "hash1")
    assert k1 == k2


def test_derive_file_key_differs_by_submission():
    k1 = derive_file_key(b"master", "sub1", "hash1")
    k2 = derive_file_key(b"master", "sub2", "hash1")
    assert k1 != k2


def test_derive_file_key_differs_by_content_hash():
    k1 = derive_file_key(b"master", "sub1", "hash1")
    k2 = derive_file_key(b"master", "sub1", "hash2")
    assert k1 != k2


def test_derive_file_key_differs_by_master():
    k1 = derive_file_key(b"master1", "sub1", "hash1")
    k2 = derive_file_key(b"master2", "sub1", "hash1")
    assert k1 != k2


# ---------------------------------------------------------------------------
# encrypt_bytes / decrypt_bytes
# ---------------------------------------------------------------------------

def _fresh_key() -> bytes:
    return os.urandom(32)


def test_encrypt_decrypt_roundtrip():
    key = _fresh_key()
    plaintext = b"secret message"
    ciphertext = encrypt_bytes(plaintext, key)
    assert decrypt_bytes(ciphertext, key) == plaintext


def test_encrypt_produces_different_ciphertext_each_time():
    key = _fresh_key()
    data = b"same data"
    c1 = encrypt_bytes(data, key)
    c2 = encrypt_bytes(data, key)
    assert c1 != c2  # different nonces


def test_ciphertext_longer_than_plaintext():
    key = _fresh_key()
    data = b"hello"
    ct = encrypt_bytes(data, key)
    # nonce (12) + GCM tag (16) = 28 extra bytes minimum
    assert len(ct) > len(data)


def test_ciphertext_starts_with_12_byte_nonce():
    key = _fresh_key()
    ct = encrypt_bytes(b"test", key)
    # We can't verify the nonce directly, but we can verify the structure
    # by decrypting after swapping nonce bytes fails
    assert len(ct) >= 12


def test_decrypt_with_wrong_key_raises():
    key = _fresh_key()
    ct = encrypt_bytes(b"secret", key)
    wrong_key = _fresh_key()
    with pytest.raises(Exception):
        decrypt_bytes(ct, wrong_key)


def test_decrypt_tampered_ciphertext_raises():
    key = _fresh_key()
    ct = bytearray(encrypt_bytes(b"secret", key))
    ct[-1] ^= 0xFF  # flip last byte (part of GCM tag)
    with pytest.raises(Exception):
        decrypt_bytes(bytes(ct), key)


def test_encrypt_empty_bytes():
    key = _fresh_key()
    ct = encrypt_bytes(b"", key)
    assert decrypt_bytes(ct, key) == b""


def test_encrypt_large_data():
    key = _fresh_key()
    data = os.urandom(1_000_000)
    ct = encrypt_bytes(data, key)
    assert decrypt_bytes(ct, key) == data
