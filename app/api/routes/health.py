from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db

router = APIRouter(prefix="/health", tags=["System Health"])


@router.get("", status_code=status.HTTP_200_OK)
def get_health_status(db: Session = Depends(get_db)):
    """
    Application health status and diagnostic checks:
    - Verifies database connectivity.
    - Reports configured AI integration provider.
    - Returns application uptime and metadata.
    """
    db_healthy = False
    try:
        # Parameterized query to check database responsiveness
        db.execute(text("SELECT 1"))
        db_healthy = True
    except Exception:
        db_healthy = False

    return {
        "status": "healthy" if db_healthy else "degraded",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database_connected": db_healthy,
        "ai_provider": settings.AI_PROVIDER,
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }
