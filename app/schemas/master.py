from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

# Bounds a base64 data: URL photo (~2.2MB raw binary at this many base64
# chars) so a client can embed an image directly in a JSON field without a
# real object-storage integration, while still capping request size abuse.
MAX_IMAGE_DATA_URL_LEN = 3_000_000


class ServiceOut(BaseModel):
    id: int
    name: str
    price: Decimal
    duration: Optional[int] = None
    description: Optional[str] = None
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    # Bounded to fit the services.price NUMERIC(10, 2) column: without this,
    # an out-of-range price crashes the request with a raw 500 from the DB
    # instead of a clean 422.
    price: Decimal = Field(..., gt=0, le=Decimal("99999999.99"), decimal_places=2)
    duration: Optional[int] = Field(default=None, gt=0, le=1440)
    description: Optional[str] = Field(default=None, max_length=2000)
    image_url: Optional[str] = Field(default=None, max_length=MAX_IMAGE_DATA_URL_LEN)


class ReviewOut(BaseModel):
    id: int
    client_name: str
    client_avatar_url: Optional[str] = None
    rating: Optional[int] = None
    text: Optional[str] = None
    service_name: Optional[str] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    text: str = Field(..., min_length=1, max_length=2000)
    service_name: Optional[str] = Field(default=None, max_length=200)
    image_url: Optional[str] = Field(default=None, max_length=MAX_IMAGE_DATA_URL_LEN)


class MasterOut(BaseModel):
    """
    Wire format matches the Flutter app's AppUser model: specialization/
    image_url here, not the Master ORM's category/photo_url column names.
    Built explicitly via master_to_out() rather than model_validate(), since
    from_attributes can't rename fields across the ORM<->API boundary.
    """

    id: int
    name: str
    username: str
    specialization: Optional[str] = None
    district: Optional[str] = None
    rating: Optional[Decimal] = None
    image_url: Optional[str] = None
    bio: Optional[str] = None
    whatsapp_phone: Optional[str] = None
    is_verified: Optional[bool] = False
    review_count: Optional[int] = 0
    services: List[ServiceOut] = []
    reviews: List[ReviewOut] = []


def master_to_out(master, *, services_limit: Optional[int] = None, include_reviews: bool = True) -> MasterOut:
    """
    master: app.models.master.Master ORM instance.

    services_limit/include_reviews let the masters-list endpoint return a
    lightweight summary (one representative service, no reviews) instead of
    every service/review with its full base64 photo repeated for every
    master on every feed load — GET /masters/{username} still returns
    everything for the one profile actually being viewed.
    """
    services = master.services[:services_limit] if services_limit is not None else master.services
    return MasterOut(
        id=master.id,
        name=master.name,
        username=master.username,
        specialization=master.category,
        district=master.district,
        rating=master.rating,
        image_url=master.photo_url,
        bio=master.bio,
        whatsapp_phone=master.whatsapp_phone,
        is_verified=master.is_verified,
        review_count=master.review_count,
        services=[ServiceOut.model_validate(s) for s in services],
        reviews=[ReviewOut.model_validate(r) for r in master.reviews] if include_reviews else [],
    )
