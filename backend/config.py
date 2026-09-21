"""
Cepa backend configuration.

All settings are driven by environment variables. The .env file (or process env)
is the single source of truth. No secrets are hardcoded here.

Usage:
    from config import settings
    print(settings.database_url)
"""
from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    storage_dir: Path = Path("./storage")
    weights_dir: Path = Path("./weights")

    # ── Grading policy ───────────────────────────────────────────────────────
    active_grading_policy: str = "DEMO_ASSUMPTION_v1"

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:8081,http://localhost:19006,exp://localhost:8081"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ── Reports ───────────────────────────────────────────────────────────────
    report_base_url: str = "http://localhost:8000"
    share_link_base_url: str = "http://localhost:8000/api/v1/reports/share"

    # ── CV inference ─────────────────────────────────────────────────────────
    cv_inference_workers: int = 2
    cv_use_gpu: bool = False

    # ── Segmentation model ───────────────────────────────────────────────────
    seg_model_path: Path = Path("./weights/yolo11n-seg.pt")
    seg_confidence_threshold: float = 0.35
    seg_iou_threshold: float = 0.45

    # ── Defect classifier ────────────────────────────────────────────────────
    def_model_path: Path = Path("./weights/defect_classifier.pt")
    def_use_mock: bool = False         # Real trained PyTorch model active

    # ── ChArUco calibration board ────────────────────────────────────────────
    charuco_square_length_mm: float = 40.0
    charuco_marker_length_mm: float = 20.0
    charuco_board_squares_x: int = 7
    charuco_board_squares_y: int = 5

    # ── Scale validation limits ───────────────────────────────────────────────
    scale_min_mm_per_px: float = 0.05
    scale_max_mm_per_px: float = 5.0

    # ── Image quality gate thresholds ────────────────────────────────────────
    qg_blur_threshold: float = 80.0
    qg_dark_threshold: int = 40
    qg_bright_threshold: int = 215
    qg_glare_fraction: float = 0.05
    qg_min_resolution_px: int = 1000

    # ── Derived paths ─────────────────────────────────────────────────────────
    @property
    def policies_dir(self) -> Path:
        return Path(__file__).parent / "grading" / "policies"

    @property
    def templates_dir(self) -> Path:
        return Path(__file__).parent / "reports" / "templates"

    def ensure_dirs(self) -> None:
        """Create required runtime directories if they don't exist."""
        for d in [
            self.storage_dir,
            self.weights_dir,
            self.storage_dir / "crops",
            self.storage_dir / "masks",
            self.storage_dir / "reports",
            self.storage_dir / "images",
        ]:
            d.mkdir(parents=True, exist_ok=True)


# Module-level singleton — import this everywhere
settings = Settings()
