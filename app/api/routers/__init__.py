from fastapi import APIRouter

from app.api.routers import buckets, files, health, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(users.router)
api_router.include_router(buckets.router)
api_router.include_router(files.router)

__all__ = ["api_router"]
