from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class ServiceOut(BaseModel):
    id: int
    name: str
    price: Decimal
    duration: Optional[int] = None
    description: Optional[str] = None

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


def master_to_out(master) -> MasterOut:
    """master: app.models.master.Master ORM instance."""
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
        services=[ServiceOut.model_validate(s) for s in master.services],
    )
