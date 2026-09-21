"""
Image Storage Service

Manages all file I/O for inspection images, crops, masks, and reports.
Uses relative paths internally — absolute paths are constructed at read time.
This makes storage portable (changing the storage directory is a config change).

Path structure:
  {storage_dir}/images/{inspection_id}/{sample_id}.jpg    — original image
  {storage_dir}/crops/{inspection_id}/{sample_id}/{idx:04d}.jpg  — onion crops
  {storage_dir}/masks/{inspection_id}/{sample_id}/{idx:04d}.png  — binary masks
  {storage_dir}/reports/{report_id}.pdf                   — generated reports
"""
from __future__ import annotations

import uuid
from pathlib import Path

from config import settings


def save_image(image_bytes: bytes, inspection_id: str) -> str:
    """
    Save a raw image upload to persistent storage.

    Returns:
        Relative path (relative to storage_dir) suitable for storing in DB.
    """
    images_dir = settings.storage_dir / "images" / inspection_id
    images_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4()}.jpg"
    abs_path = images_dir / filename
    abs_path.write_bytes(image_bytes)

    # Return relative path (relative to storage_dir)
    rel_path = f"images/{inspection_id}/{filename}"
    return rel_path


def get_absolute_path(relative_path: str) -> Path:
    """Convert a stored relative path to an absolute filesystem path."""
    return settings.storage_dir / relative_path


def path_to_url(relative_path: str | None, base_url: str | None = None) -> str | None:
    """
    Build a URL for serving a stored file.

    For the PoC, files are served directly by FastAPI's StaticFiles.
    The URL pattern is: /static/{relative_path}
    """
    if relative_path is None:
        return None
    base = base_url or settings.report_base_url.rstrip("/")
    return f"{base}/static/{relative_path}"
