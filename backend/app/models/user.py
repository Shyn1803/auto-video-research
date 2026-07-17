"""User model"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
	__tablename__ = 'users'

	id: Mapped[UUID] = mapped_column(
		PG_UUID(as_uuid=True), primary_key=True,
		server_default='gen_random_uuid()',
	)
	email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
	password_hash: Mapped[str] = mapped_column(Text, nullable=False)
	display_name: Mapped[str] = mapped_column(Text, nullable=False)
	role: Mapped[str] = mapped_column(nullable=False, server_default='creator')
	is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='true')
	must_change_password: Mapped[bool] = mapped_column(
		Boolean, nullable=False, server_default='false',
	)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), nullable=False, server_default='now()',
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), nullable=False, server_default='now()',
	)

	__table_args__ = (
		CheckConstraint(
			"role IN ('admin', 'creator')", name='ck_users_role',
		),
	)
