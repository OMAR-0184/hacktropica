from datetime import timedelta
import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from api.database.core import get_db
from api.database.models import User
from api.schemas.auth import UserCreate, UserProfileUpdate, UserResponse, Token
from api.schemas.learning import LoginRequest
from api.engine.auth_utils import (
    verify_password,
    get_password_hash,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
    ALGORITHM,
)

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 32
USERNAME_PATTERN = re.compile(r"^[a-z0-9_]+$")


def _normalize_and_validate_username(username: str) -> str:
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


def _username_base_from_email(email: str) -> str:
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


async def _generate_unique_username(db: AsyncSession, email: str) -> str:
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


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalars().first()

    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.email == user.email))
    db_user = result.scalars().first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    if user.username is not None:
        username = _normalize_and_validate_username(user.username)
        username_result = await db.execute(select(User).filter(User.username == username))
        if username_result.scalars().first():
            raise HTTPException(status_code=409, detail="Username already taken")
    else:
        username = await _generate_unique_username(db, user.email)

    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, username=username, password_hash=hashed_password)

    db.add(new_user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        email_conflict = await db.execute(select(User).filter(User.email == user.email))
        if email_conflict.scalars().first():
            raise HTTPException(status_code=409, detail="Email already registered")

        username_conflict = await db.execute(select(User).filter(User.username == username))
        if username_conflict.scalars().first():
            raise HTTPException(status_code=409, detail="Username already taken")

        raise HTTPException(status_code=409, detail="Unable to register user due to a unique constraint conflict")
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
):
    """Login via form-data (required by OAuth2/Swagger UI)."""
    return await _authenticate_and_create_token(form_data.username, form_data.password, db)


@router.post("/login/json", response_model=Token)
async def login_json(
    login_req: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login via JSON body — the standard for modern SPA frontends.

    Request body: {"email": "...", "password": "..."}
    """
    return await _authenticate_and_create_token(login_req.email, login_req.password, db)


@router.get("/me", response_model=UserResponse, deprecated=True)
async def read_users_me(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Deprecated alias for /auth/profile kept for backward compatibility.
    """
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</auth/profile>; rel="successor-version"'
    return await get_user_profile(current_user=current_user, db=db)


@router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).filter(User.id == current_user.id))
    user = result.scalars().first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/profile", response_model=UserResponse)
async def update_user_profile(
    payload: UserProfileUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    username = _normalize_and_validate_username(payload.username)
    result = await db.execute(select(User).filter(User.id == current_user.id))
    user = result.scalars().first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    existing = await db.execute(
        select(User).filter(User.username == username, User.id != current_user.id)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="Username already taken")

    user.username = username
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Username already taken")
    await db.refresh(user)
    return user


async def _authenticate_and_create_token(email: str, password: str, db: AsyncSession) -> dict:
    """Shared auth logic for both form-data and JSON login endpoints."""
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
