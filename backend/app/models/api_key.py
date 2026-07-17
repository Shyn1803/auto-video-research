"""ApiKey model — Fernet-encrypted API key for provider framework (Task 3-4 FR-15)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ApiKey(Base):
    """Encrypted-at-rest API key row.

    Plaintext is NEVER stored — ``key_encrypted`` holds Fernet ciphertext
    (base64-encoded, so ``Text`` column is sufficient).  Decrypt only
    into memory, gate access through ``KeyService``.
    """

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    # Fernet ciphertext — see app/core/crypto.py for encrypt/decrypt.
    key_encrypted: Mapped[bytes] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active", index=True
    )
    usage_count: Mapped[int] = mapped_column(nullable=False, server_default="0")
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    exhausted_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'exhausted', 'revoked')",
            name="ck_api_keys_status",
        ),
    )
