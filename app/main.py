from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from app import models  # noqa: F401  ensures all models are registered on Base.metadata
from app.api.v1.endpoints import auth, masters, notifications, posts
from app.core.config import settings
from app.db.migrations import run_migrations
from app.db.session import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await run_migrations()
    yield


app = FastAPI(
    title="Bi Bi API",
    description="Backend API for Bi Bi beauty masters app: auth + masters in one server",
    version="1.0.0",
    lifespan=lifespan,
)

# Bearer-token auth (Authorization header) does not need cookies, so
# allow_credentials stays False — that's what makes a wildcard origin list safe.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Responses here are base64-photo-heavy JSON (masters/posts/reviews), which
# compresses well over the wire — meaningful win for users on slow/mobile
# connections, cheap to add.
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.state.limiter = auth.limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(status_code=429, content={"detail": "Too many requests, slow down"})


@app.get("/")
async def root():
    return {"status": "ok", "message": "Bi Bi API is running"}


app.include_router(auth.router)
app.include_router(auth.me_router)
app.include_router(masters.router)
app.include_router(posts.router)
app.include_router(notifications.router)
