"""
Cepa Backend Application Entrypoint

FastAPI app factory, lifespan handlers, CORS middleware, static file serving,
and route registration.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from database import create_all_tables
from routers import health, inspections, reports
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
    
    # 1. Ensure required runtime storage directories exist
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

# ── CORS Middleware ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permissive for mobile Expo / dev environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static File Serving (Crops, Masks, Reports, Images) ───────────────────────
settings.ensure_dirs()
app.mount("/static", StaticFiles(directory=str(settings.storage_dir)), name="static")

# ── Interactive Mandi Inspector Web Studio ────────────────────────────────────
from fastapi.responses import FileResponse, RedirectResponse
static_ui_dir = Path(__file__).parent / "static"
if static_ui_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(static_ui_dir)), name="ui")

@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/inspector")

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
            filename="cepa_charuco_7x5_calibration_board_A4.pdf"
        )
    return {"message": "Calibration board PDF not found"}

# ── Register Routers ──────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(inspections.router)
app.include_router(reports.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
