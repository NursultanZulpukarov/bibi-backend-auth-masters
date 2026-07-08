import re
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.master import MAX_IMAGE_DATA_URL_LEN, ReviewOut, ServiceOut

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
    image_url: Optional[str] = Field(default=None, max_length=MAX_IMAGE_DATA_URL_LEN)

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


class UpdateProfileRequest(BaseModel):
    """
    All fields optional and only applied when present, so a client can PATCH
    just the one field it changed. bio/specialization/district only take
    effect for accounts that have a linked Master row — silently ignored
    for plain clients rather than erroring, since a client PATCHing its own
    display name shouldn't need to know it's not a master.
    """

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    image_url: Optional[str] = Field(default=None, max_length=MAX_IMAGE_DATA_URL_LEN)
    bio: Optional[str] = Field(default=None, max_length=500)
    specialization: Optional[str] = Field(default=None, max_length=50)
    district: Optional[str] = Field(default=None, max_length=100)


class UserOut(BaseModel):
    """
    Wire format matches the Flutter app's single AppUser model (used for both
    "myself" and "masters browsed in the directory"), so field names here are
    image_url/bio/specialization/district — not the User/Master ORM attribute
    names. For master accounts these are filled in from the linked Master row
    by build_user_out() in the auth endpoints; they stay None for clients.
    """

    id: int
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str = "client"
    name: Optional[str] = ""
    image_url: Optional[str] = None
    bio: Optional[str] = None
    specialization: Optional[str] = None
    district: Optional[str] = None
    rating: Optional[Decimal] = None
    review_count: Optional[int] = 0
    services: List[ServiceOut] = []
    reviews: List[ReviewOut] = []


class AuthResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    user: UserOut


def build_user_out(user, master=None) -> UserOut:
    """
    user: app.models.user.User, master: app.models.master.Master | None
    Not type-hinted against the ORM classes to avoid a schemas->models->schemas
    import cycle risk; callers always pass the real ORM instances.
    """
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        phone=user.phone,
        role=user.role,
        name=user.name,
        image_url=(master.photo_url if master else None) or user.avatar_url,
        bio=master.bio if master else None,
        specialization=master.category if master else None,
        district=master.district if master else None,
        rating=master.rating if master else None,
        review_count=master.review_count if master else 0,
        services=[ServiceOut.model_validate(s) for s in master.services] if master else [],
        reviews=[ReviewOut.model_validate(r) for r in master.reviews] if master else [],
    )
