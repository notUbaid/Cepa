"""Health check router."""
from __future__ import annotations

import platform
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from services.inspection_service import get_cv_status

router = APIRouter(prefix="/api/v1", tags=["health"])

_DEMO_SAMPLE_PATH = (
    Path(__file__).resolve().parent.parent
    / "static"
    / "demo_onion_spread.jpg"
)


@router.get("/health")
async def health() -> dict:
    """Basic liveness check."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
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


_DEMO_VIDEO_PATH = Path(__file__).resolve().parent.parent / "storage" / "demo_onion_sweep.mp4"

@router.get("/demo/sample-video")
async def get_demo_sample_video():
    """Returns a verified demo onion sweep video."""
    if _DEMO_VIDEO_PATH.exists():
        return FileResponse(
            _DEMO_VIDEO_PATH,
            media_type="video/mp4",
            filename="demo_onion_sweep.mp4",
        )
    raise HTTPException(status_code=404, detail="Demo sample video not found on disk")

