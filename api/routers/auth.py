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
    SECRET_KEY,
    ALGORITHM,
)
from api.services.user_service import (
    normalize_and_validate_username,
    generate_unique_username,
    authenticate_and_create_token,
)

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


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
        username = normalize_and_validate_username(user.username)
        username_result = await db.execute(
            select(User).filter(User.username == username)
        )
        if username_result.scalars().first():
            raise HTTPException(status_code=409, detail="Username already taken")
    else:
        username = await generate_unique_username(db, user.email)

    from api.engine.auth_utils import get_password_hash

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

        username_conflict = await db.execute(
            select(User).filter(User.username == username)
        )
        if username_conflict.scalars().first():
            raise HTTPException(status_code=409, detail="Username already taken")

        raise HTTPException(
            status_code=409,
            detail="Unable to register user due to a unique constraint conflict",
        )
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
):
    """Login via form-data (required by OAuth2/Swagger UI)."""
    return await authenticate_and_create_token(
        form_data.username, form_data.password, db
    )


@router.post("/login/json", response_model=Token)
async def login_json(
    login_req: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login via JSON body — the standard for modern SPA frontends.

    Request body: {"email": "...", "password": "..."}
    """
    return await authenticate_and_create_token(login_req.email, login_req.password, db)


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
    username = normalize_and_validate_username(payload.username)
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
