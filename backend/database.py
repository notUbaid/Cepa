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

from config import settings


# SQLite-specific: enable WAL mode and foreign key enforcement.
# These pragmas only apply to SQLite; they are no-ops for other engines.
def _sqlite_connect_listener(dbapi_connection, connection_record):  # noqa: ANN001
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
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

    # Lightweight SQLite auto-migration for newly added columns
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            res = conn.execute(text("PRAGMA table_info(samples)")).fetchall()
            existing_cols = {row[1] for row in res}
            if "is_estimated_scale" not in existing_cols:
                conn.execute(text("ALTER TABLE samples ADD COLUMN is_estimated_scale BOOLEAN DEFAULT 0"))
            if "calibration_method" not in existing_cols:
                conn.execute(text("ALTER TABLE samples ADD COLUMN calibration_method VARCHAR(50) DEFAULT 'CHARUCO_BOARD'"))

            res_insp = conn.execute(text("PRAGMA table_info(inspections)")).fetchall()
            existing_insp_cols = {row[1] for row in res_insp}
            if "farmer_id" not in existing_insp_cols:
                conn.execute(text("ALTER TABLE inspections ADD COLUMN farmer_id VARCHAR(50)"))
            if "farmer_name" not in existing_insp_cols:
                conn.execute(text("ALTER TABLE inspections ADD COLUMN farmer_name VARCHAR(150)"))

            conn.commit()
        except Exception:
            pass
