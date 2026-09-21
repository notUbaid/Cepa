"""Health check router."""
from __future__ import annotations

import platform
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from services.inspection_service import get_cv_status

router = APIRouter(prefix="/api/v1", tags=["health"])

_DEMO_SAMPLE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "cv_tools"
    / "test_data"
    / "synthetic_onion_spread_sample.jpg"
)


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


@router.get("/demo/sample-image")
async def get_demo_sample_image():
    """Returns a verified high-resolution onion spread sample with ChArUco card."""
    if _DEMO_SAMPLE_PATH.exists():
        return FileResponse(
            _DEMO_SAMPLE_PATH,
            media_type="image/jpeg",
            filename="demo_onion_spread.jpg",
        )
    raise HTTPException(status_code=404, detail="Demo sample image not found on disk")
