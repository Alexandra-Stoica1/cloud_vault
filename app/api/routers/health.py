from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import AppSettings, DbSession

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health(session: DbSession, settings: AppSettings) -> dict[str, str]:
    """Liveness + database connectivity check."""
    session.execute(text("SELECT 1"))
    return {"status": "ok", "app": settings.app_name}
