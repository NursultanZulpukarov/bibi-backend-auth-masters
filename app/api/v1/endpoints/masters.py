from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.db.session import get_db
from app.models.master import Master
from app.schemas.master import MasterOut

router = APIRouter()


@router.get("/masters", response_model=List[MasterOut])
async def get_masters(
    category: Optional[str] = Query(default=None, description="Filter by category (e.g. hair, nails, makeup)"),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Master)
        .options(selectinload(Master.services))
        .where(Master.is_active == True)
    )

    if category:
        stmt = stmt.where(Master.category == category)

    result = await db.execute(stmt)
    return result.scalars().all()
