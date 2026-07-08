from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.master import MAX_IMAGE_DATA_URL_LEN


class PostCreate(BaseModel):
    image_url: str = Field(..., max_length=MAX_IMAGE_DATA_URL_LEN)
    service_id: Optional[int] = None


class PostOut(BaseModel):
    id: int
    image_url: Optional[str] = None
    master_username: str
    master_name: str
    master_avatar_url: Optional[str] = None
    service_id: Optional[int] = None
    service_name: Optional[str] = None
    service_price: Optional[Decimal] = None
    service_duration: Optional[int] = None
    service_description: Optional[str] = None
    like_count: int = 0
    is_liked_by_me: bool = False
    is_saved_by_me: bool = False
    created_at: Optional[datetime] = None
