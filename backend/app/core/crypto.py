"""Fernet envelope — the single point that touches raw API key bytes.

Every API key encrypts/decrypts through this module with the master key
sourced from FERNET_MASTER_KEY env var (KMS on cloud).

Design constraints:
- Plaintext never touches a DB column (key_encrypted stores Fernet ciphertext).
- Plaintext never appears in response bodies (only masked form).
- Only api_key_service calls encrypt/decrypt. No other code path touches key bytes.
"""

from __future__ import annotations

import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("avr.crypto")

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = os.environ.get("FERNET_MASTER_KEY", "")
        if not key:
            raise RuntimeError(
                "FERNET_MASTER_KEY is not set. "
                "Generate one: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        _fernet = Fernet(key)
    return _fernet


def encrypt(plaintext: str) -> bytes:
    if not isinstance(plaintext, str):
        raise TypeError(f"encrypt expects str, got {type(plaintext).__name__}")
    return _get_fernet().encrypt(plaintext.encode("utf-8"))


def decrypt(ciphertext: bytes) -> str:
    if not ciphertext:
        return ""
    try:
        return _get_fernet().decrypt(bytes(ciphertext)).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("invalid ciphertext — wrong FERNET_MASTER_KEY or corrupted data") from exc


def mask(plaintext: str) -> str:
    if not plaintext:
        return ""
    if len(plaintext) <= 10:
        return plaintext[:4] + "****"
    return plaintext[:6] + "..." + plaintext[-4:]
