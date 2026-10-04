"""
Cepa backend configuration.

All settings are driven by environment variables. The .env file (or process env)
is the single source of truth. No secrets are hardcoded here.

Usage:
    from config import settings
    print(settings.database_url)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("cepa.config")


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Nested env vars use __ separator (pydantic-settings convention).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Core ────────────────────────────────────────────────────────────────
    backend_env: str = "development"
    log_level: str = "INFO"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./cepa.db"

    # ── Storage ──────────────────────────────────────────────────────────────
    storage_dir: Path = (
        Path(os.environ["STORAGE_DIR"])
        if "STORAGE_DIR" in os.environ
        else Path(__file__).resolve().parent / "storage"
    )
    weights_dir: Path = Path(__file__).resolve().parent / "weights"

    # ── Grading policy ───────────────────────────────────────────────────────
    active_grading_policy: str = "DEMO_ASSUMPTION_v1"

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: str = (
        "http://localhost:8081,http://localhost:19006,exp://localhost:8081,"
        "http://localhost:8000,http://127.0.0.1:8000,http://localhost:8001,http://127.0.0.1:8001,"
        "http://localhost:3000,http://localhost:4173,http://127.0.0.1:4173,"
        "https://cepa-app.vercel.app,https://cepa-nine.vercel.app"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ── Reports ───────────────────────────────────────────────────────────────
    report_base_url: str = "http://localhost:8000"
    share_link_base_url: str = "http://localhost:8000/api/v1/reports/share"

    # ── CV inference ─────────────────────────────────────────────────────────
    cv_inference_workers: int = 2
    cv_use_gpu: bool = False

    # ── Groq Multimodal AI ───────────────────────────────────────────────────
    # Active multimodal model (qwen/qwen3.8-27b on Groq)
    groq_api_key: str = ""
    groq_vision_model: str = "qwen/qwen3.8-27b"
    groq_text_model: str = "qwen/qwen3.8-27b"

    # ── Bhashini Multilingual Speech Synthesis (NLTM) ────────────────────────
    bhashini_api_key: str = ""
    bhashini_user_id: str = ""
    bhashini_inference_api_key: str = ""

    # ── Segmentation model ───────────────────────────────────────────────────
    seg_model_path: Path = Path(__file__).resolve().parent / "weights" / "yolo11n-seg.pt"
    seg_confidence_threshold: float = 0.25
    seg_iou_threshold: float = 0.45

    # ── Security & Authentication ────────────────────────────────────────────
    officer_api_key: str = "cepa-officer-secret-key-2026"
    enforce_officer_auth: bool = False  # Set to True in production to strictly require X-Officer-Token
    # Separate dedicated HMAC secret for tamper-evident report seals
    hmac_seal_secret_key: str = "cepa-sovereign-seal-secret-2026-v2"

    # ── Upload Limits ────────────────────────────────────────────────────────
    max_image_upload_mb: int = 25
    max_video_upload_mb: int = 100
    max_audio_upload_mb: int = 10

    def_model_path: Path = Path(__file__).resolve().parent / "weights" / "defect_classifier.pt"
    def_use_mock: bool = False         # Real trained deep model is active

    # ── ChArUco calibration board ────────────────────────────────────────────
    charuco_square_length_mm: float = 40.0
    charuco_marker_length_mm: float = 20.0
    charuco_board_squares_x: int = 7
    charuco_board_squares_y: int = 5

    # ── Scale validation limits ───────────────────────────────────────────────
    scale_min_mm_per_px: float = 0.05
    scale_max_mm_per_px: float = 5.0

    # ── Image quality gate thresholds ────────────────────────────────────────
    qg_blur_threshold: float = 35.0
    qg_dark_threshold: int = 25
    # Raised from 235 → 245: white/cream onion surfaces are inherently high-luma
    qg_bright_threshold: int = 245
    # Raised from 0.15 → 0.45: onion outer tunics and white backgrounds
    # naturally contain large fractions of near-white (>250) pixels.
    # True specular glare causes >50% of pixels to be blown out.
    qg_glare_fraction: float = 0.45
    qg_min_resolution_px: int = 300

    # ── Derived paths ─────────────────────────────────────────────────────────
    @property
    def policies_dir(self) -> Path:
        return Path(__file__).parent / "grading" / "policies"

    @property
    def templates_dir(self) -> Path:
        return Path(__file__).parent / "reports" / "templates"

    def ensure_dirs(self) -> None:
        """Create required runtime directories if they don't exist."""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            fallback = Path(__file__).resolve().parent / "storage"
            logger.warning("Could not create storage_dir %s (%s). Falling back to %s", self.storage_dir, e, fallback)
            self.storage_dir = fallback
            self.storage_dir.mkdir(parents=True, exist_ok=True)

        for d in [
            self.storage_dir,
            self.weights_dir,
            self.storage_dir / "crops",
            self.storage_dir / "masks",
            self.storage_dir / "reports",
            self.storage_dir / "images",
        ]:
            try:
                d.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.warning("Could not ensure directory %s: %s", d, e)


# Module-level singleton -- import this everywhere
settings = Settings()

import sys
if __name__ in ("config", "backend.config"):
    sys.modules["config"] = sys.modules[__name__]
    sys.modules["backend.config"] = sys.modules[__name__]
