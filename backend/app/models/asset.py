"""Asset model -- licensed media record (Task 5-3, FR-20).

Every asset entering the system (stock download, user upload, future
AI-generated image) gets exactly one row here with ``license`` populated --
"unknown license" is never a valid state (rules/security.md). Matches
docs/specs/database-schema.md §2.5 ``assets`` table.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

if TYPE_CHECKING:
    pass


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    license: Mapped[str] = mapped_column(Text, nullable=False)
    attribution_required: Mapped[bool] = mapped_column(nullable=False, default=False)
    attribution_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str] = mapped_column(String(10), nullable=False, server_default="image")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_by: Mapped[PG_UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    __table_args__ = (
        CheckConstraint(
            "media_type IN ('image', 'video', 'audio')", name="ck_assets_media_type"
        ),
        CheckConstraint("license <> ''", name="ck_assets_license_not_empty"),
    )
