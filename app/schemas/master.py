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
    price: Decimal = Field(..., gt=0)
    duration: Optional[int] = Field(default=None, gt=0)
    description: Optional[str] = Field(default=None, max_length=2000)


class MasterOut(BaseModel):
    id: int
    name: str
    username: str
    category: Optional[str] = None
    district: Optional[str] = None
    rating: Optional[Decimal] = None
    photo_url: Optional[str] = None
    whatsapp_phone: Optional[str] = None
    is_verified: Optional[bool] = False
    review_count: Optional[int] = 0
    services: List[ServiceOut] = []

    class Config:
        from_attributes = True
