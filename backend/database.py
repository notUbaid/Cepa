"""
Database setup: SQLAlchemy engine, session factory, and base model.

Uses SQLite for the PoC. To switch to PostgreSQL, change DATABASE_URL in .env.
The same ORM code works unchanged — only the connection string needs updating.

Session dependency for FastAPI route injection:
    from database import get_db
    def my_route(db: Session = Depends(get_db)): ...
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

try:
    from backend.config import settings
except ImportError:
    from config import settings


# SQLite-specific: enable WAL mode and foreign key enforcement.
# These pragmas only apply to SQLite; they are no-ops for other engines.
def _sqlite_connect_listener(dbapi_connection, connection_record):  # noqa: ANN001
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=(settings.backend_env == "development"),
)

# Register SQLite pragmas listener only for SQLite connections
if settings.database_url.startswith("sqlite"):
    event.listen(engine, "connect", _sqlite_connect_listener)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.
    Ensures the session is always closed, even if an exception occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables() -> None:
    """
    Create all tables defined in ORM models and apply lightweight SQLite migrations.
    """
    import models  # noqa: F401 — side-effect import registers models
    Base.metadata.create_all(bind=engine)

    import logging
    logger = logging.getLogger(__name__)

    # Lightweight SQLite auto-migration for newly added columns
    if is_sqlite:
        from sqlalchemy import text
        with engine.connect() as conn:
            try:
                res = conn.execute(text("PRAGMA table_info(samples)")).fetchall()
                existing_cols = {row[1] for row in res}
                if "is_estimated_scale" not in existing_cols:
                    conn.execute(text("ALTER TABLE samples ADD COLUMN is_estimated_scale BOOLEAN DEFAULT 0"))
                if "calibration_method" not in existing_cols:
                    conn.execute(text("ALTER TABLE samples ADD COLUMN calibration_method VARCHAR(50) DEFAULT 'CHARUCO_BOARD'"))
                if "image_sha256" not in existing_cols:
                    conn.execute(text("ALTER TABLE samples ADD COLUMN image_sha256 VARCHAR(64)"))
                if "corner_count" not in existing_cols:
                    conn.execute(text("ALTER TABLE samples ADD COLUMN corner_count INTEGER DEFAULT 0"))
                if "reprojection_residual_px" not in existing_cols:
                    conn.execute(text("ALTER TABLE samples ADD COLUMN reprojection_residual_px FLOAT"))
                if "board_coverage_pct" not in existing_cols:
                    conn.execute(text("ALTER TABLE samples ADD COLUMN board_coverage_pct FLOAT"))

                res_insp = conn.execute(text("PRAGMA table_info(inspections)")).fetchall()
                existing_insp_cols = {row[1] for row in res_insp}
                if "farmer_id" not in existing_insp_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN farmer_id VARCHAR(50)"))
                if "farmer_name" not in existing_insp_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN farmer_name VARCHAR(150)"))
                if "cut_test_performed" not in existing_insp_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN cut_test_performed BOOLEAN DEFAULT 0"))
                if "cut_test_bulbs_count" not in existing_insp_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN cut_test_bulbs_count INTEGER DEFAULT 0"))
                if "cut_test_internal_defects_found" not in existing_insp_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN cut_test_internal_defects_found INTEGER DEFAULT 0"))
                if "cut_test_notes" not in existing_insp_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN cut_test_notes TEXT"))
                if "provenance_json" not in existing_insp_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN provenance_json TEXT"))

                res_rep = conn.execute(text("PRAGMA table_info(reports)")).fetchall()
                existing_rep_cols = {row[1] for row in res_rep}
                if "cryptographic_seal" not in existing_rep_cols:
                    conn.execute(text("ALTER TABLE reports ADD COLUMN cryptographic_seal VARCHAR(64)"))
                if "image_sha256" not in existing_rep_cols:
                    conn.execute(text("ALTER TABLE reports ADD COLUMN image_sha256 VARCHAR(64)"))
                if "seal_status" not in existing_rep_cols:
                    conn.execute(text("ALTER TABLE reports ADD COLUMN seal_status VARCHAR(32) DEFAULT 'PENDING'"))
                if "cut_test_performed" not in existing_rep_cols:
                    conn.execute(text("ALTER TABLE reports ADD COLUMN cut_test_performed BOOLEAN DEFAULT 0"))
                if "cut_test_bulbs_count" not in existing_rep_cols:
                    conn.execute(text("ALTER TABLE reports ADD COLUMN cut_test_bulbs_count INTEGER DEFAULT 0"))
                if "cut_test_internal_defects_found" not in existing_rep_cols:
                    conn.execute(text("ALTER TABLE reports ADD COLUMN cut_test_internal_defects_found INTEGER DEFAULT 0"))
                if "cut_test_notes" not in existing_rep_cols:
                    conn.execute(text("ALTER TABLE reports ADD COLUMN cut_test_notes TEXT"))
                if "reissued_from_id" not in existing_rep_cols:
                    conn.execute(text("ALTER TABLE reports ADD COLUMN reissued_from_id VARCHAR(36)"))
                if "report_version" not in existing_rep_cols:
                    conn.execute(text("ALTER TABLE reports ADD COLUMN report_version INTEGER DEFAULT 1"))
                if "status" not in existing_rep_cols:
                    conn.execute(text("ALTER TABLE reports ADD COLUMN status VARCHAR(20) DEFAULT 'ACTIVE'"))
                if "manifest_hash" not in existing_rep_cols:
                    conn.execute(text("ALTER TABLE reports ADD COLUMN manifest_hash VARCHAR(64)"))
                if "pdf_sha256" not in existing_rep_cols:
                    conn.execute(text("ALTER TABLE reports ADD COLUMN pdf_sha256 VARCHAR(64)"))
                if "evidence_manifest_json" not in existing_rep_cols:
                    conn.execute(text("ALTER TABLE reports ADD COLUMN evidence_manifest_json TEXT"))
                if "provenance_json" not in existing_rep_cols:
                    conn.execute(text("ALTER TABLE reports ADD COLUMN provenance_json TEXT"))

                conn.commit()
            except Exception as e:
                logger.warning("SQLite auto-migration warning: %s", e)
