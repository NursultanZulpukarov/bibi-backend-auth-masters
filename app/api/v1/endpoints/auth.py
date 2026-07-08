from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.master import Master
from app.models.user import User
from app.schemas.user import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
    UserOut,
    build_user_out,
)

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["auth"])
me_router = APIRouter(tags=["auth"])


async def _get_master_for(db: AsyncSession, user: User) -> Master | None:
    if user.role != "master":
        return None
    result = await db.execute(
        select(Master)
        .options(selectinload(Master.services), selectinload(Master.reviews))
        .where(Master.user_id == user.id)
    )
    return result.scalar_one_or_none()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(request: Request, payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    conditions = [User.username == payload.username]
    if payload.email:
        conditions.append(User.email == payload.email.lower())
    if payload.phone:
        conditions.append(User.phone == payload.phone)

    result = await db.execute(select(User).where(or_(*conditions)))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this username, email or phone already exists",
        )

    try:
        password_hash = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    user = User(
        username=payload.username,
        email=payload.email.lower() if payload.email else None,
        phone=payload.phone,
        password_hash=password_hash,
        role=payload.role,
        name=payload.name or payload.username,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    master = None
    if payload.role == "master":
        # A Master row with this username must not already exist: auto-linking to it
        # here would let anyone silently take over a pre-existing business profile
        # (reviews, verified badge, etc.) just by registering with a matching username.
        existing_master = (
            await db.execute(select(Master).where(Master.username == payload.username))
        ).scalar_one_or_none()
        if existing_master is not None:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A master profile with this username already exists",
            )

        master = Master(
            username=payload.username,
            user_id=user.id,
            name=payload.name or user.username,
            category=payload.specialization or "other",
            district=payload.district,
            bio=payload.bio,
            photo_url=payload.image_url,
        )
        db.add(master)

    try:
        await db.commit()
    except IntegrityError:
        # Rare race: another request registered the same master username between
        # our check above and this commit. Surface it as a normal conflict
        # instead of a raw 500.
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    await db.refresh(user)
    if master is not None:
        # Re-fetch with services eager-loaded (freshly created, so always empty,
        # but this keeps the shape consistent with login/me).
        master = await _get_master_for(db, user)

    token = create_access_token(user.id)
    return AuthResponse(token=token, user=build_user_out(user, master))


@router.post("/login", response_model=AuthResponse)
@limiter.limit("20/minute")
async def login(request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    login_val = payload.login.strip()
    result = await db.execute(
        select(User).where(
            or_(
                User.email == login_val.lower(),
                User.username == login_val,
                User.phone == login_val,
            )
        )
    )
    user = result.scalar_one_or_none()
    password_ok = verify_password(payload.password, user.password_hash if user else DUMMY_HASH)

    if not user or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    master = await _get_master_for(db, user)
    token = create_access_token(user.id)
    return AuthResponse(token=token, user=build_user_out(user, master))


@me_router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    master = await _get_master_for(db, current_user)
    return build_user_out(current_user, master)


@me_router.patch("/me", response_model=UserOut)
async def update_me(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.name is not None:
        current_user.name = payload.name
    if payload.image_url is not None:
        current_user.avatar_url = payload.image_url
    db.add(current_user)

    master = await _get_master_for(db, current_user)
    if master is not None:
        if payload.name is not None:
            master.name = payload.name
        if payload.image_url is not None:
            master.photo_url = payload.image_url
        if payload.bio is not None:
            master.bio = payload.bio
        if payload.specialization is not None:
            master.category = payload.specialization
        if payload.district is not None:
            master.district = payload.district
        db.add(master)

    await db.commit()
    await db.refresh(current_user)
    if master is not None:
        master = await _get_master_for(db, current_user)
    return build_user_out(current_user, master)
