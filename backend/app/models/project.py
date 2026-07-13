"""Project model — owns lifecycle, mode, formats, and voice settings."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.step_version import StepVersion


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    owner_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="interactive"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="DRAFT"
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False, server_default="vi")
    formats: Mapped[list[str]] = mapped_column(
        Text, nullable=False, server_default="{vertical_1080x1920}"
    )
    voice_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cloned_from: Mapped[PG_UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    step_versions: Mapped[list[StepVersion]] = relationship(
        "StepVersion", back_populates="project", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "mode IN ('interactive', 'daily_news')", name="ck_projects_mode"
        ),
        CheckConstraint(
            "status IN ('DRAFT','RESEARCHING','NEED_REVIEW','REVISING',"
            "'APPROVED','PRODUCING','RENDERING','READY',"
            "'PUBLISHING','PUBLISHED','FAILED','ARCHIVED')",
            name="ck_projects_status",
        ),
        CheckConstraint(
            "voice_gender IS NULL OR voice_gender IN ('female', 'male')",
            name="ck_projects_voice_gender",
        ),
    )
