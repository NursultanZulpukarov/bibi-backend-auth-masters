from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal


class ServiceOut(BaseModel):
    id: int
    title: str
    price: Decimal
    duration_minutes: int
    description: str

    class Config:
        from_attributes = True


class MasterOut(BaseModel):
    id: int
    name: str
    username: str
    category: Optional[str]
    district: Optional[str]
    rating: Optional[Decimal]
    photo_url: Optional[str]
    whatsapp_phone: Optional[str]
    services: List[ServiceOut] = []

    class Config:
        from_attributes = True
