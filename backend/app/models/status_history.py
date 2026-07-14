"""StatusHistory model — immutable audit log for project status transitions."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.project import Project


class StatusHistory(Base):
    """One row per status transition on a project.

    The ``actor`` column stores ``user_id`` | ``"system"`` | agent node
    name per BR-2. ``reason`` is nullable for normal transitions but
    required (at service level) for abnormal ones (→FAILED, overrides).

    Rows are append-only: the application never UPDATEs or DELETEs a
    history row.
    """

    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,  # BIGINT GENERATED ALWAYS AS IDENTITY
    )
    project_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    to_status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    actor: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )

    project: Mapped[Project] = relationship(
        "Project",
        back_populates="status_history",
    )
