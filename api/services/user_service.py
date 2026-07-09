"""
User account operations — registration helpers and authentication logic.

Extracted from the auth router to keep endpoint handlers thin.
"""

from __future__ import annotations

import re
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models import User
from api.engine.auth_utils import (
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

# ── Username constraints ──────────────────────────────────────

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 32
USERNAME_PATTERN = re.compile(r"^[a-z0-9_]+$")


def normalize_and_validate_username(username: str) -> str:
    """Normalise and validate a username, raising HTTP 422 on failure."""
    normalized = username.strip().lower()
    if not normalized:
        raise HTTPException(status_code=422, detail="Username cannot be empty")
    if len(normalized) < USERNAME_MIN_LENGTH or len(normalized) > USERNAME_MAX_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"Username must be between {USERNAME_MIN_LENGTH} and {USERNAME_MAX_LENGTH} characters",
        )
    if not USERNAME_PATTERN.match(normalized):
        raise HTTPException(
            status_code=422,
            detail="Username can contain only lowercase letters, numbers, and underscores",
        )
    return normalized


# ── Username generation ───────────────────────────────────────


def _username_base_from_email(email: str) -> str:
    """Derive a username base from the local part of an email address."""
    local = email.split("@", 1)[0].lower()
    cleaned = re.sub(r"[^a-z0-9_]+", "_", local).strip("_")
    cleaned = re.sub(r"_+", "_", cleaned)
    if not cleaned:
        cleaned = "learner"
    if cleaned[0].isdigit():
        cleaned = f"user_{cleaned}"
    if len(cleaned) < USERNAME_MIN_LENGTH:
        cleaned = f"{cleaned}_user"
    return cleaned[:USERNAME_MAX_LENGTH]


async def generate_unique_username(db: AsyncSession, email: str) -> str:
    """Generate a username that doesn't collide with existing ones."""
    base = _username_base_from_email(email)
    candidate = base
    suffix = 1
    while True:
        result = await db.execute(select(User).filter(User.username == candidate))
        if result.scalars().first() is None:
            return candidate
        suffix_text = f"_{suffix}"
        prefix_limit = USERNAME_MAX_LENGTH - len(suffix_text)
        candidate = f"{base[:prefix_limit]}{suffix_text}"
        suffix += 1


# ── Authentication ────────────────────────────────────────────


async def authenticate_and_create_token(
    email: str, password: str, db: AsyncSession
) -> dict:
    """Verify credentials and return an access-token dict."""
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalars().first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
