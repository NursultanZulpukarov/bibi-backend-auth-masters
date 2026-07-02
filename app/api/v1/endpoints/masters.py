from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.endpoints.auth import limiter
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.master import Master, Service
from app.models.user import User
from app.schemas.master import MasterOut, ServiceCreate, ServiceOut, master_to_out

router = APIRouter(tags=["masters"])


@router.get("/masters", response_model=List[MasterOut])
async def get_masters(
    specialization: Optional[str] = Query(default=None, description="Filter by category (e.g. hair, nails, makeup)"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Master)
        .options(selectinload(Master.services))
        .where(Master.is_active.is_(True))
        .order_by(Master.id)
        .limit(limit)
        .offset(offset)
    )

    if specialization:
        stmt = stmt.where(Master.category == specialization)

    result = await db.execute(stmt)
    return [master_to_out(m) for m in result.scalars().all()]


@router.get("/masters/{username}", response_model=MasterOut)
async def get_master_profile(username: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Master)
        .options(selectinload(Master.services))
        .where(Master.username == username, Master.is_active.is_(True))
    )
    result = await db.execute(stmt)
    master = result.scalar_one_or_none()
    if master is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master not found")
    return master_to_out(master)


@router.post("/masters/services", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def add_service(
    request: Request,
    payload: ServiceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "master":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only masters can add services",
        )

    result = await db.execute(select(Master).where(Master.user_id == current_user.id))
    master = result.scalar_one_or_none()
    if master is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Master profile not found for this account",
        )

    service = Service(
        master_id=master.id,
        name=payload.name,
        price=payload.price,
        duration=payload.duration,
        description=payload.description,
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service
