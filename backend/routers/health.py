"""Health check router."""
from __future__ import annotations

import json
import logging
import platform
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Response
from fastapi.responses import FileResponse

from services.inspection_service import get_cv_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["health"])

_DEMO_SAMPLE_PATH = (
    Path(__file__).resolve().parent.parent
    / "static"
    / "synthetic_demo_spread.jpg"
)


@router.get("/health")
@router.get("/health/live")
async def health_liveness(response: Response) -> dict:
    """
    Kubernetes/container liveness check: confirms process is alive and event loop is responsive.
    In production, returns 503 if core CV pipeline models failed to load or are mock.
    """
    from config import settings

    cv = get_cv_status()
    is_ready = bool(cv.get("seg_ready"))
    is_prod = settings.backend_env.lower() in ("production", "prod")

    if is_prod and (not is_ready or cv.get("seg_is_mock") or cv.get("defect_is_mock")):
        response.status_code = 503
        return {
            "status": "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "cepa-backend",
            "environment": settings.backend_env,
            "cv": cv,
        }

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "cepa-backend",
        "version": "0.1.0",
        "python": platform.python_version(),
        "is_mock": bool(cv.get("seg_is_mock") or cv.get("defect_is_mock")),
    }


@router.get("/health/ready")
async def health_readiness() -> dict:
    """
    Readiness probe: validates all downstream operational subsystems before routing traffic.
    Checks: database connectivity, storage write permissions, CV pipeline readiness, and grading policy.
    """
    checks = {}
    is_ready = True

    # 1. Database check
    from database import engine
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok", "engine": "sqlite" if "sqlite" in str(engine.url) else "postgresql"}
    except Exception as e:
        checks["database"] = {"status": "failed", "error": str(e)}
        is_ready = False

    # 2. Storage directory check
    from config import settings
    try:
        storage_dir = settings.storage_dir
        storage_dir.mkdir(parents=True, exist_ok=True)
        probe_file = storage_dir / ".readiness_probe"
        probe_file.write_text("probe", encoding="utf-8")
        probe_file.unlink(missing_ok=True)
        checks["storage"] = {"status": "ok", "path": str(storage_dir)}
    except Exception as e:
        checks["storage"] = {"status": "failed", "error": str(e)}
        is_ready = False

    # 3. CV Subsystems & Policy check
    cv = get_cv_status()
    checks["cv_pipeline"] = {
        "status": "ok" if cv.get("seg_ready") else "degraded",
        "segmentation": cv.get("seg_provider"),
        "defect_classifier": cv.get("defect_classifier"),
        "active_policy": cv.get("active_policy"),
        "policy_verified": cv.get("policy_verified"),
    }
    if not cv.get("seg_ready"):
        is_ready = False

    status_code = 200 if is_ready else 503
    payload = {
        "status": "ready" if is_ready else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
    if not is_ready:
        from fastapi import Response
        return Response(
            content=json.dumps(payload),
            status_code=503,
            media_type="application/json",
        )
    return payload


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
    """Returns a synthetic onion spread composite sample with ChArUco card."""
    if _DEMO_SAMPLE_PATH.exists():
        return FileResponse(
            _DEMO_SAMPLE_PATH,
            media_type="image/jpeg",
            filename="synthetic_demo_spread.jpg",
        )
    raise HTTPException(status_code=404, detail="Demo sample image not found on disk")


_DEMO_VIDEO_PATHS = [
    Path(__file__).resolve().parent.parent / "static" / "demo_onion_sweep.mp4",
    Path(__file__).resolve().parent.parent / "storage" / "demo_onion_sweep.mp4",
]


@router.get("/demo/sample-video")
async def get_demo_sample_video():
    """Returns a verified demo onion sweep video."""
    for p in _DEMO_VIDEO_PATHS:
        if p.exists():
            return FileResponse(
                p,
                media_type="video/mp4",
                filename="demo_onion_sweep.mp4",
            )

    # Synthesize fallback clip on the fly if neither file is found
    fallback_path = Path(__file__).resolve().parent.parent / "static" / "demo_onion_sweep.mp4"
    try:
        import cv2
        import numpy as np
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(str(fallback_path), fourcc, 10.0, (320, 240))
        for _ in range(10):
            frame = np.full((240, 320, 3), 120, dtype=np.uint8)
            cv2.circle(frame, (160, 120), 40, (30, 40, 180), -1)
            out.write(frame)
        out.release()
        if fallback_path.exists():
            return FileResponse(
                fallback_path,
                media_type="video/mp4",
                filename="demo_onion_sweep.mp4",
            )
    except Exception as e:
        logger.warning("Could not synthesize fallback demo video: %s", e)

    raise HTTPException(status_code=404, detail="Demo sample video not found on disk")


@router.post("/demo/seed-inspection")
async def seed_demo_inspection(
    force_reprocess: bool = False,
    x_officer_token: str | None = Header(default=None, alias="X-Officer-Token"),
):
    """
    Creates or retrieves a verified demo inspection.
    When force_reprocess=True, runs the full live CV pipeline on the demo image.
    Enforces officer authentication when force_reprocess=True to prevent unauthorized sample deletion.
    """
    if force_reprocess:
        from auth import verify_officer_token
        verify_officer_token(x_officer_token)

    from database import get_db, SessionLocal
    from models import Inspection, Sample
    from schemas import InspectionCreate
    from services import inspection_service
    from routers.inspections import _inspection_to_detail

    db = SessionLocal()
    try:
        existing = db.query(Inspection).filter(Inspection.lot_id == "LOT-NASHIK-RED-DEMO").first()
        if existing and existing.samples and not force_reprocess:
            return _inspection_to_detail(existing, db)

        inspection = existing
        if not inspection:
            body = InspectionCreate(
                lot_id="LOT-NASHIK-RED-DEMO",
                procurement_centre="Lasalgaon APMC Mandi, Nashik",
                officer_name="Inspector Patil",
                officer_id="MH-NSK-104",
                notes="Mandi intake demonstration: Nashik Red cultivar under autonomous overhead heuristic calibration",
            )
            inspection = inspection_service.create_inspection(db, body)
            inspection.farmer_name = "Ramesh Patil"
            inspection.farmer_id = "MH-NAS-2026-8842"
            db.commit()
        elif force_reprocess:
            inspection.status = "IN_PROGRESS"
            for s in list(inspection.samples):
                db.delete(s)
            db.commit()

        if _DEMO_SAMPLE_PATH.exists() and (not inspection.samples or force_reprocess):
            with open(_DEMO_SAMPLE_PATH, "rb") as f:
                image_bytes = f.read()
            await inspection_service.process_sample_image(
                db=db,
                inspection_id=inspection.id,
                image_bytes=image_bytes,
            )

        db.refresh(inspection)
        return _inspection_to_detail(inspection, db)
    finally:
        db.close()


