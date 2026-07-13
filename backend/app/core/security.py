"""Password hashing — argon2id with OWASP parameters."""

from datetime import timedelta, timezone
from typing import Any

import argon2
from fastapi import HTTPException
from jwt import DecodeError, ExpiredSignatureError, PyJWT


ph = argon2.PasswordHasher(
    time_cost=2,
    memory_cost=102400,
    parallelism=8,
    hash_len=32,
    salt_len=16,
)

MIN_PASSWORD_LENGTH = 10


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        ph.verify(hashed, password)
        return True
    except argon2.exceptions.VerifyMismatchError:
        return False


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")


def create_access_token(
    subject: str,
    role: str,
    *,
    expires_delta: timedelta | None = None,
    secret: str,
    algorithm: str = "HS256",
) -> str:
    import jwt as _jwt
    now = datetime now(timezone.utc)
    exp = now + (expires_delta or timedelta(minutes=15))
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str, *, secret: str, algorithm: str = "HS256") -> dict[str, Any]:
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except (ExpiredSignatureError, DecodeError):
        raise HTTPException(status_code=401, detail="invalid token")
