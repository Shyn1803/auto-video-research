"""Fernet envelope — the single point that touches raw API key bytes.

Every API key flows through Fernet encrypt/decrypt with the master key
sourced from ``FERNET_MASTER_KEY`` env var (or KMS on cloud deploys).

Design constraints (from rules/security.md):
- Plaintext never appears in DB columns, response bodies, or log lines.
- The only consumers are ``api_key_service`` (save/get) and
  ``provider_settings.resolve`` (key → adapter at dispatch time).
"""

from __future__ import annotations

import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("avr.crypto")

# ---------------------------------------------------------------------------
# Singleton-ish: one Fernet instance per process (master key never changes
# at runtime — a restart is required for key rotation, which is handled
# by pair key FERNET_MASTER_KEY_V2 in task 10-4).
# ---------------------------------------------------------------------------

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Return the process-wide Fernet instance; read key from env once."""
    global _fernet
    if _fernet is None:
        key = os.environ.get("FERNET_MASTER_KEY", "")
        if not key:
            raise RuntimeError(
                "FERNET_MASTER_KEY is not set — API keys cannot be stored. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\""
            )
        _fernet = Fernet(key)
    return _fernet


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def encrypt(plaintext: str) -> bytes:
    """Return Fernet ciphertext as bytes."""
    if not isinstance(plaintext, str):
        raise TypeError("encrypt expects str, got %s" % type(plaintext).__name__)
    return _get_fernet().encrypt(plaintext.encode("utf-8"))


def decrypt(ciphertext: bytes | None) -> str:
    """Return plaintext string; empty string on empty input."""
    if not ciphertext:
        return ""
    try:
        return _get_fernet().decrypt(bytes(ciphertext)).decode("utf-8")
    except InvalidToken:
        logger.error("crypto.decrypt InvalidToken — ciphertext was not produced by this Fernet key")
        raise
    except Exception:
        logger.exception("crypto.decrypt unexpected error")
        raise


def mask(plaintext: str) -> str:
    """Return a masked representation for safe display in responses.

    Examples: ``AIZa...x4Kq``, ``sk-...ab12``.
    Never logs or returns more than 6 plaintext chars.
    """
    if not plaintext:
        return ""
    length = len(plaintext)
    if length <= 10:
        return plaintext[:4] + "****"
    return plaintext[:6] + "..." + plaintext[-4:]
