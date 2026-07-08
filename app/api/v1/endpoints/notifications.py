from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import limiter
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.master import Master, Service
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationOut


class BookingCreate(BaseModel):
    service_id: Optional[int] = None
    message: Optional[str] = Field(default=None, max_length=500)

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=List[NotificationOut])
async def list_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    notification = result.scalar_one_or_none()
    if notification is None or notification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notification.unread = False
    await db.commit()
    await db.refresh(notification)
    return notification


@router.post("/masters/{username}/book", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def request_booking(
    request: Request,
    username: str,
    payload: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lightweight "Записаться" action: no calendar/slots system exists, so this
    creates a real Notification for the master (using the pre-existing,
    previously-unused notifications table) rather than a fake button that
    goes nowhere.
    """
    master = (
        await db.execute(select(Master).where(Master.username == username, Master.is_active.is_(True)))
    ).scalar_one_or_none()
    if master is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master not found")
    if master.user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot book yourself")
    if master.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This master cannot receive bookings")

    service_name = None
    if payload.service_id is not None:
        service = (
            await db.execute(
                select(Service).where(Service.id == payload.service_id, Service.master_id == master.id)
            )
        ).scalar_one_or_none()
        if service is not None:
            service_name = service.name

    client_label = current_user.name or current_user.username
    text = f"{client_label} хочет записаться" + (f" на «{service_name}»" if service_name else "")
    if payload.message:
        text += f": {payload.message}"

    notification = Notification(
        user_id=master.user_id,
        title="Новая заявка на запись",
        text=text,
        type="booking_request",
    )
    db.add(notification)
    await db.commit()
    return {"status": "ok"}
