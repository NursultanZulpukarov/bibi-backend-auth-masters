from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: int
    title: str
    text: str
    type: Optional[str] = None
    unread: Optional[bool] = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
