"""Health check router."""
from __future__ import annotations

import platform
from datetime import datetime

from fastapi import APIRouter

from services.inspection_service import get_cv_status

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Basic liveness check."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "cepa-backend",
        "version": "0.1.0",
        "python": platform.python_version(),
    }


@router.get("/health/cv")
async def cv_health() -> dict:
    """CV pipeline component status."""
    cv = get_cv_status()
    return {
        "status": "ok" if cv["seg_ready"] else "degraded",
        **cv,
    }
