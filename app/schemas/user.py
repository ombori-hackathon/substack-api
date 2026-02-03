import re
from typing import Optional

import pytz
from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain at least one special character")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    id: int
    email: str
    email_notifications_enabled: bool
    push_notifications_enabled: bool
    timezone: str

    class Config:
        from_attributes = True


class NotificationPreferencesUpdate(BaseModel):
    email_notifications_enabled: Optional[bool] = None
    push_notifications_enabled: Optional[bool] = None
    timezone: Optional[str] = None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        if v is not None and v not in pytz.all_timezones:
            raise ValueError(f"Invalid timezone: {v}")
        return v


class NotificationPreferencesResponse(BaseModel):
    email_notifications_enabled: bool
    push_notifications_enabled: bool
    timezone: str

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
