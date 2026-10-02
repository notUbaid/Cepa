"""
Image Storage Service

Manages all file I/O for inspection images, crops, masks, and reports.
Uses relative paths internally -- absolute paths are constructed at read time.
This makes storage portable (changing the storage directory is a config change).

Path structure:
  {storage_dir}/images/{inspection_id}/{sample_id}.jpg    -- original image
  {storage_dir}/crops/{inspection_id}/{sample_id}/{idx:04d}.jpg  -- onion crops
  {storage_dir}/masks/{inspection_id}/{sample_id}/{idx:04d}.png  -- binary masks
  {storage_dir}/reports/{report_id}.pdf                   -- generated reports
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


def path_to_url(
    relative_path: str | None,
    base_url: str | None = None,
    share_token: str | None = None,
) -> str | None:
    """
    Build an authorized URL for serving a stored file.
    The URL pattern is: /api/v1/storage/{relative_path}
    """
    if relative_path is None or not str(relative_path).strip():
        return None
    clean_path = str(relative_path).replace("\\", "/").lstrip("/")
    if base_url:
        url = f"{base_url.rstrip('/')}/api/v1/storage/{clean_path}"
    else:
        url = f"/api/v1/storage/{clean_path}"
    if share_token:
        url += f"?token={share_token}"
    return url
