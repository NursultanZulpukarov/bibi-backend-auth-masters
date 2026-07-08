from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.endpoints.auth import limiter
from app.core.security import get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.master import Master, Service
from app.models.post import Post, PostLike, PostSave
from app.models.user import User
from app.schemas.post import PostCreate, PostOut

router = APIRouter(tags=["posts"])


async def _current_master(db: AsyncSession, user: User) -> Master:
    if user.role != "master":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only masters can do this")
    result = await db.execute(select(Master).where(Master.user_id == user.id))
    master = result.scalar_one_or_none()
    if master is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master profile not found for this account")
    return master


async def _build_posts_out(
    db: AsyncSession,
    pairs: List[tuple],
    current_user_id: Optional[int],
) -> List[PostOut]:
    """pairs: list of (Post, Master) tuples, already carrying Post.service eager-loaded."""
    if not pairs:
        return []
    post_ids = [p.id for p, _ in pairs]

    like_count_rows = await db.execute(
        select(PostLike.post_id, func.count(PostLike.user_id))
        .where(PostLike.post_id.in_(post_ids))
        .group_by(PostLike.post_id)
    )
    like_counts = dict(like_count_rows.all())

    liked_ids: set = set()
    saved_ids: set = set()
    if current_user_id is not None:
        liked_rows = await db.execute(
            select(PostLike.post_id).where(PostLike.post_id.in_(post_ids), PostLike.user_id == current_user_id)
        )
        liked_ids = set(liked_rows.scalars().all())
        saved_rows = await db.execute(
            select(PostSave.post_id).where(PostSave.post_id.in_(post_ids), PostSave.user_id == current_user_id)
        )
        saved_ids = set(saved_rows.scalars().all())

    out = []
    for post, master in pairs:
        service = post.service
        out.append(
            PostOut(
                id=post.id,
                image_url=post.image_url,
                master_username=master.username,
                master_name=master.name,
                master_avatar_url=master.photo_url,
                service_id=service.id if service else None,
                service_name=service.name if service else None,
                service_price=service.price if service else None,
                service_duration=service.duration if service else None,
                service_description=service.description if service else None,
                like_count=like_counts.get(post.id, 0),
                is_liked_by_me=post.id in liked_ids,
                is_saved_by_me=post.id in saved_ids,
                created_at=post.created_at,
            )
        )
    return out


@router.post("/masters/posts", response_model=PostOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_post(
    request: Request,
    payload: PostCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    master = await _current_master(db, current_user)

    if payload.service_id is not None:
        result = await db.execute(
            select(Service).where(Service.id == payload.service_id, Service.master_id == master.id)
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Service does not belong to you")

    post = Post(master_id=current_user.id, service_id=payload.service_id, image_url=payload.image_url)
    db.add(post)
    await db.commit()
    await db.refresh(post)

    result = await db.execute(
        select(Post).options(selectinload(Post.service)).where(Post.id == post.id)
    )
    post = result.scalar_one()
    out = await _build_posts_out(db, [(post, master)], current_user.id)
    return out[0]


@router.get("/masters/{username}/posts", response_model=List[PostOut])
async def list_master_posts(
    username: str,
    limit: int = Query(default=30, ge=1, le=60),
    offset: int = Query(default=0, ge=0),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Master).where(Master.username == username, Master.is_active.is_(True)))
    master = result.scalar_one_or_none()
    if master is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master not found")
    if master.user_id is None:
        return []

    stmt = (
        select(Post)
        .options(selectinload(Post.service))
        .where(Post.master_id == master.user_id)
        .order_by(Post.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    posts = (await db.execute(stmt)).scalars().all()
    pairs = [(post, master) for post in posts]
    return await _build_posts_out(db, pairs, current_user.id if current_user else None)


@router.get("/posts", response_model=List[PostOut])
async def explore_posts(
    specialization: Optional[str] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=60),
    offset: int = Query(default=0, ge=0),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Post, Master)
        .join(Master, Master.user_id == Post.master_id)
        .options(selectinload(Post.service))
        .where(Master.is_active.is_(True), Post.image_url.is_not(None))
        .order_by(Post.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if specialization:
        stmt = stmt.where(Master.category == specialization)

    rows = (await db.execute(stmt)).all()
    pairs = [(post, master) for post, master in rows]
    return await _build_posts_out(db, pairs, current_user.id if current_user else None)


@router.get("/me/liked-posts", response_model=List[PostOut])
async def my_liked_posts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Post, Master)
        .join(PostLike, PostLike.post_id == Post.id)
        .join(Master, Master.user_id == Post.master_id)
        .options(selectinload(Post.service))
        .where(PostLike.user_id == current_user.id)
        .order_by(Post.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    pairs = [(post, master) for post, master in rows]
    return await _build_posts_out(db, pairs, current_user.id)


@router.get("/me/saved-posts", response_model=List[PostOut])
async def my_saved_posts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Post, Master)
        .join(PostSave, PostSave.post_id == Post.id)
        .join(Master, Master.user_id == Post.master_id)
        .options(selectinload(Post.service))
        .where(PostSave.user_id == current_user.id)
        .order_by(Post.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    pairs = [(post, master) for post, master in rows]
    return await _build_posts_out(db, pairs, current_user.id)


@router.post("/posts/{post_id}/like")
async def toggle_like(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    existing = (
        await db.execute(
            select(PostLike).where(PostLike.post_id == post_id, PostLike.user_id == current_user.id)
        )
    ).scalar_one_or_none()

    if existing is not None:
        await db.delete(existing)
        liked = False
    else:
        db.add(PostLike(post_id=post_id, user_id=current_user.id))
        liked = True
    await db.commit()

    count = (
        await db.execute(select(func.count(PostLike.user_id)).where(PostLike.post_id == post_id))
    ).scalar_one()
    return {"liked": liked, "like_count": count}


@router.post("/posts/{post_id}/save")
async def toggle_save(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    existing = (
        await db.execute(
            select(PostSave).where(PostSave.post_id == post_id, PostSave.user_id == current_user.id)
        )
    ).scalar_one_or_none()

    if existing is not None:
        await db.delete(existing)
        saved = False
    else:
        db.add(PostSave(post_id=post_id, user_id=current_user.id))
        saved = True
    await db.commit()
    return {"saved": saved}


@router.delete("/masters/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.master_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your post")
    await db.delete(post)
    await db.commit()
