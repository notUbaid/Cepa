"""
Upload validation and security module.

Enforces MIME type checking, extension validation, and memory-safe chunked
size limits to protect backend servers from out-of-memory (OOM) denial-of-service
attacks caused by oversized uploads.
"""
from __future__ import annotations

import logging
from typing import Set
from fastapi import HTTPException, UploadFile, status

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES: Set[str] = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}

ALLOWED_VIDEO_TYPES: Set[str] = {
    "video/mp4",
    "video/quicktime",  # .mov
    "video/webm",
}

ALLOWED_AUDIO_TYPES: Set[str] = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
}


async def validate_and_read_upload(
    upload_file: UploadFile,
    allowed_types: Set[str],
    max_mb: int,
    label: str = "Uploaded file",
) -> bytes:
    """
    Validate MIME type, extension, and enforce strict memory-safe chunked size limits.

    Raises:
        HTTPException(415): If MIME type or extension is not permitted.
        HTTPException(413): If file exceeds max_mb size cap.
        HTTPException(400): If file is empty.
    """
    if not upload_file or not upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} is required.",
        )

    # 1. Content-type and extension validation
    raw_content_type = (upload_file.content_type or "").lower().split(";")[0].strip()
    filename_lower = upload_file.filename.lower()

    # Determine permitted extensions for allowed types
    valid_ext = False
    if "image/jpeg" in allowed_types or "image/png" in allowed_types:
        if filename_lower.endswith((".jpg", ".jpeg", ".png", ".webp")):
            valid_ext = True
    if "video/mp4" in allowed_types:
        if filename_lower.endswith((".mp4", ".mov", ".webm")):
            valid_ext = True
    if "audio/wav" in allowed_types:
        if filename_lower.endswith((".wav", ".wave", ".mp3")):
            valid_ext = True

    if raw_content_type not in allowed_types and not valid_ext:
        logger.warning(
            "Rejected upload '%s' with invalid content-type: %s",
            upload_file.filename,
            upload_file.content_type,
        )
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported format for {label} ('{upload_file.content_type}'). "
                f"Allowed formats: {sorted(allowed_types)}"
            ),
        )

    # 2. Chunked reading with hard size limit (prevents reading entire 2GB file into memory)
    max_bytes = max_mb * 1024 * 1024
    chunk_size = 512 * 1024  # 512 KB chunks
    chunks: list[bytes] = []
    total_bytes = 0

    while True:
        chunk = await upload_file.read(chunk_size)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            logger.warning(
                "Upload '%s' exceeded size limit of %d MB (current: %d bytes)",
                upload_file.filename,
                max_mb,
                total_bytes,
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"{label} exceeds maximum allowed size of {max_mb} MB.",
            )
        chunks.append(chunk)

    if total_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} is empty (0 bytes).",
        )

    return b"".join(chunks)
