import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def sha256_bytes(data: bytes) -> str:
    """Return the SHA-256 hex digest of arbitrary bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    """Return the SHA-256 hex digest of a file, reading in 64 KiB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def derive_file_key(master_key: bytes, submission_id: str, content_hash: str) -> bytes:
    """
    Derive a deterministic AES-256 key for a specific file using a keyed hash.
    Key is unique per (master_key, submission_id, content_hash) triple.
    """
    context = f"{submission_id}:{content_hash}".encode()
    return hashlib.sha256(master_key + context).digest()


def encrypt_bytes(data: bytes, key: bytes) -> bytes:
    """
    Encrypt data with AES-256-GCM.
    Returns: nonce (12 bytes) || ciphertext+tag
    """
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return nonce + ciphertext


def decrypt_bytes(payload: bytes, key: bytes) -> bytes:
    """
    Decrypt AES-256-GCM payload produced by encrypt_bytes.
    Expects nonce prepended to ciphertext+tag.
    """
    nonce = payload[:12]
    ciphertext = payload[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)
