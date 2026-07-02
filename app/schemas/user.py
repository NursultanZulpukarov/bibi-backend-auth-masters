import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")
PHONE_RE = re.compile(r"^\+?[0-9]{10,15}$")


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str = Field(..., min_length=6, max_length=72)
    role: str = Field(default="client")
    name: str = Field(default="")
    bio: Optional[str] = Field(default=None, max_length=500)
    specialization: Optional[str] = Field(default=None, max_length=50)
    district: Optional[str] = Field(default=None, max_length=100)
    image_url: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not USERNAME_RE.match(v):
            raise ValueError("username must be 3-30 chars: letters, digits, underscore")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = v.replace(" ", "").replace("-", "")
        if not PHONE_RE.match(cleaned):
            raise ValueError("invalid phone format")
        return cleaned

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("client", "master"):
            raise ValueError("role must be 'client' or 'master'")
        return v


class LoginRequest(BaseModel):
    login: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=72)


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str = "client"
    name: Optional[str] = ""
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    user: UserOut
