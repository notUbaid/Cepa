"""
Protected Storage and Media Router.

Serves inspection images, crops, masks, and generated PDF reports with access
control. Prevents directory traversal and unauthenticated enumeration of farmer
records and biometric/geospatial sample data (DPDP compliance).
"""
from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.report import Report

logger = logging.getLogger(__name__)
router = APIRouter(tags=["storage"])

MIME_TYPE_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".pdf": "application/pdf",
    ".mp4": "video/mp4",
}


def _verify_storage_access(
    file_path: str,
    token: str | None,
    x_officer_token: str | None,
    db: Session,
) -> None:
    """
    Validate that the requester has permission to access the specified file.
    In production (ENFORCE_OFFICER_AUTH=true), access requires either:
      1. A valid X-Officer-Token header matching settings.officer_api_key, OR
      2. A valid share_token query parameter corresponding to the requested inspection/report.
    """
    if not settings.enforce_officer_auth:
        return

    # Officer authentication header
    import hmac
    if x_officer_token and hmac.compare_digest(x_officer_token, settings.officer_api_key):
        return

    # Public share token validation
    if token:
        report = db.query(Report).filter(Report.share_token == token).first()
        if report:
            norm_path = file_path.replace("\\", "/").strip("/")
            # Check if this file belongs to the report's inspection or report id
            if norm_path.startswith("reports/"):
                if Path(norm_path).stem == str(report.report_id):
                    return
            elif (
                norm_path.startswith("images/")
                or norm_path.startswith("crops/")
                or norm_path.startswith("masks/")
            ):
                parts = norm_path.split("/")
                if len(parts) >= 2 and parts[1] == str(report.inspection_id):
                    return
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security: Provided token is not authorized for this resource.",
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Security: Authentication required. Provide X-Officer-Token header or ?token=<share_token>.",
        headers={"WWW-Authenticate": "ApiKey"},
    )


@router.get("/api/v1/storage/{file_path:path}")
async def serve_stored_file(
    file_path: str,
    token: str | None = Query(None, description="Public inspection share token for authorized access"),
    x_officer_token: str | None = Header(None, alias="X-Officer-Token"),
    db: Session = Depends(get_db),
) -> FileResponse:
    """
    Authorized endpoint to fetch inspection media and generated certificates.
    Guarded against path traversal and unauthorized bulk access.
    """
    import os
    base_dir = os.path.abspath(str(settings.storage_dir))
    target_path = os.path.abspath(os.path.join(base_dir, file_path))

    # Guard against directory traversal attacks (e.g., ../../etc/passwd)
    try:
        if os.path.commonpath([base_dir, target_path]) != base_dir:
            logger.warning("Directory traversal attempt blocked: %s", file_path)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security: Invalid file path traversal blocked.",
            )
    except (ValueError, OSError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security: Invalid file path traversal blocked.",
        )

    try:
        if not (os.path.exists(target_path) and os.path.isfile(target_path)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requested file not found.",
            )
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested file not found.",
        )

    target = Path(target_path)

    _verify_storage_access(file_path=file_path, token=token, x_officer_token=x_officer_token, db=db)

    ext = target.suffix.lower()
    media_type = MIME_TYPE_MAP.get(ext) or mimetypes.guess_type(str(target))[0] or "application/octet-stream"

    return FileResponse(
        path=str(target),
        media_type=media_type,
        filename=target.name,
    )
