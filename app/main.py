from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import masters

app = FastAPI(
    title="Bi Bi API",
    description="Backend API for Bi Bi beauty masters app",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # На проде заменить на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(masters.router, prefix="/api/v1", tags=["masters"])


@app.get("/")
async def root():
    return {"status": "ok", "message": "Bi Bi API is running"}