from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str | None = None


class UserProfileUpdate(BaseModel):
    username: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str


class RefreshRequest(BaseModel):
    refresh_token: str
