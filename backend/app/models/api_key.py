"""ApiKey model — Fernet-encrypted API key storage.

Every secret passed through the Fernet envelope (FERNET_MASTER_KEY from env).
Plaintext never touches the DB column; the masked form is computed on-the-fly
for response shaping (service layer, never in the model).

See docs/specs/database-schema.md §2.7.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import ClassVar

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Index,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ApiKey(Base):
    """Encrypted raw material for a provider credential.

    The ``key_encrypted`` column holds Fernet ciphertext (BYTEA).  The
    ``fernet`` module in ``api_key_service`` is the only code path that
    touches the raw bytes.  No plaintext API key is ever SELECTed
    outside that service.
    """

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    key_encrypted: Mapped[bytes] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="active"
    )
    usage_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0"
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    exhausted_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'exhausted', 'revoked', 'invalid')",
            name="ck_api_keys_status",
        ),
        Index("idx_api_keys_provider", "provider", "status"),
    )
