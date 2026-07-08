from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.endpoints.auth import limiter
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.master import Master, Review, Service
from app.models.user import User
from app.schemas.master import (
    MasterOut,
    ReviewCreate,
    ReviewOut,
    ServiceCreate,
    ServiceOut,
    master_to_out,
)

router = APIRouter(tags=["masters"])


def _master_query(*, with_reviews: bool = True):
    # When with_reviews is True, reviews are eager-loaded here (not lazily)
    # because master_to_out() reads master.reviews — under the async engine a
    # lazy load there would crash with "greenlet_spawn has not been called",
    # not just be slow. The masters-list endpoint skips this: it doesn't need
    # every master's full review history (each with its own photo) just to
    # render a feed card, so there's no point loading it from the DB either.
    options = [selectinload(Master.services)]
    if with_reviews:
        options.append(selectinload(Master.reviews))
    return select(Master).options(*options)


@router.get("/masters", response_model=List[MasterOut])
async def get_masters(
    specialization: Optional[str] = Query(default=None, description="Filter by category (e.g. hair, nails, makeup)"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        _master_query(with_reviews=False)
        .where(Master.is_active.is_(True))
        .order_by(Master.id)
        .limit(limit)
        .offset(offset)
    )

    if specialization:
        stmt = stmt.where(Master.category == specialization)

    result = await db.execute(stmt)
    # Summary shape for the list view: one representative service (with its
    # photo) so feed cards still have something to show, no reviews — full
    # detail is a single extra request away via GET /masters/{username}.
    return [master_to_out(m, services_limit=1, include_reviews=False) for m in result.scalars().all()]


@router.get("/masters/{username}", response_model=MasterOut)
async def get_master_profile(username: str, db: AsyncSession = Depends(get_db)):
    stmt = _master_query().where(Master.username == username, Master.is_active.is_(True))
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
        image_url=payload.image_url,
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service


@router.post(
    "/masters/{username}/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED
)
@limiter.limit("10/minute")
async def add_review(
    request: Request,
    username: str,
    payload: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Master).where(Master.username == username, Master.is_active.is_(True))
    )
    master = result.scalar_one_or_none()
    if master is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master not found")

    if master.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot leave a review on your own profile",
        )

    review = Review(
        master_id=master.id,
        client_name=current_user.name or current_user.username,
        client_avatar_url=current_user.avatar_url,
        rating=payload.rating,
        text=payload.text,
        service_name=payload.service_name,
        image_url=payload.image_url,
        user_id=current_user.id,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review
