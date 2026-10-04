"""
Cepa Backend Application Entrypoint

FastAPI app factory, lifespan handlers, CORS middleware, static file serving,
and route registration.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from config import settings
from database import create_all_tables, get_db
from routers import health, inspections, reports, storage
from services.inspection_service import initialize_cv_components

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cepa")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes runtime directories, database tables, and CV/grading components once at startup.
    """
    logger.info("Initializing Cepa backend service (env=%s)...", settings.backend_env)

    # Bound PyTorch CPU threads to reduce thread pool memory overhead on resource-constrained containers (Render 512MB free tier)
    try:
        import torch
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
    except Exception:
        pass

    # 1. Validate security posture
    settings.validate_security_configuration()

    # 2. Ensure required runtime storage directories exist
    settings.ensure_dirs()

    # 2. Ensure database tables exist
    create_all_tables()
    logger.info("Database initialized with URL: %s", settings.database_url)

    # 3. Initialize CV models and active grading policy
    try:
        initialize_cv_components()
        logger.info("CV pipeline and grading policy initialized successfully.")
    except Exception as e:
        logger.exception("Failed to initialize CV components during startup: %s", e)
        # We don't crash the server so health checks and diagnostics can still report errors

    # 4. Automatically seed demo data if database is empty (ephemeral Render recovery)
    try:
        from services.seed_service import seed_demo_data_if_empty
        seed_demo_data_if_empty()
    except Exception as e:
        logger.warning("Failed to auto-seed demo data at startup: %s", e)

    yield

    logger.info("Cepa backend shutting down cleanly.")


app = FastAPI(
    title="Cepa Onion Quality Inspection API",
    description=(
        "SIH26031: AI-powered onion quality inspection, size calibration, "
        "defect classification, and grading policy enforcement."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Middleware
# allow_origins handles exact configured origins (localhost dev & configured domains).
# allow_origin_regex allows production CEPA Vercel deployments (cepa-app, cepa-nine, and branch previews).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"^https://(cepa-app|cepa-nine|cepa-[a-z0-9-]+)\.vercel\.app$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Interactive Mandi Inspector Web Studio
static_ui_dir = Path(__file__).parent / "static"
if static_ui_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(static_ui_dir)), name="ui")


@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/inspector")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    fav_path = static_ui_dir / "logo.png"
    if fav_path.exists():
        return FileResponse(fav_path, media_type="image/png")
    from fastapi import Response
    return Response(status_code=204)


@app.get("/inspector", include_in_schema=False)
async def serve_inspector():
    index_path = static_ui_dir / "inspector.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Inspector UI not found"}


@app.get("/deck", include_in_schema=False)
async def serve_deck():
    deck_path = static_ui_dir / "deck.html"
    if deck_path.exists():
        return FileResponse(deck_path)
    return {"message": "Presentation deck not found"}


@app.get("/calibration-board", include_in_schema=False)
async def download_calibration_board():
    pdf_path = static_ui_dir / "charuco_board_7x5_40mm_A4_printable.pdf"
    if pdf_path.exists():
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename="cepa_charuco_7x5_calibration_board_A4.pdf",
        )
    return {"message": "Calibration board PDF not found"}


# Protected legacy /static bridge -- routes through secure storage verification
@app.get("/static/{file_path:path}", include_in_schema=False)
async def protected_static_proxy(
    file_path: str,
    token: str | None = None,
    x_officer_token: str | None = Header(None, alias="X-Officer-Token"),
    db: Session = Depends(get_db),
):
    return await storage.serve_stored_file(
        file_path=file_path,
        token=token,
        x_officer_token=x_officer_token,
        db=db,
    )


# Register Routers
app.include_router(health.router)
app.include_router(inspections.router)
app.include_router(reports.router)
app.include_router(storage.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
