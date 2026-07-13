"""Idempotent admin seed — reads ADMIN_EMAIL / ADMIN_PASSWORD from settings."""

from sqlalchemy import insert, select

from app.core.config import get_settings
from app.core.database import Database
from app.core.security import hash_password, validate_password
from app.models.user import User


async def seed_admin() -> None:
    settings = get_settings()
    validate_password(settings.admin_password)

    db = Database(settings.database_url)
    async with db._engine.connect() as conn:
        existing = (await conn.execute(select(User).where(User.email == settings.admin_email))).scalar_one_or_none()
        if existing is not None:
            return
        await conn.execute(insert(User).values(
            id=__import__("uuid").uuid4(),
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            display_name=settings.admin_email.split("@")[0],
            role="admin",
            is_active=True,
        ))
        await conn.commit()
