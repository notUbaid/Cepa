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
    # Standard JPEG
    "image/jpeg",
    "image/jpg",
    "image/pjpeg",
    "image/jfif",
    # Portable Network Graphics
    "image/png",
    "image/x-png",
    # Modern WebP
    "image/webp",
    # High Efficiency Image Container (Apple iOS native camera format)
    "image/heic",
    "image/heif",
    "image/heic-sequence",
    "image/heif-sequence",
    # Bitmap
    "image/bmp",
    "image/x-bmp",
    "image/x-ms-bmp",
    # Tagged Image File Format
    "image/tiff",
    "image/x-tiff",
    # AV1 Image File Format
    "image/avif",
    "image/avifs",
    # Graphics Interchange Format (stills)
    "image/gif",
}

ALLOWED_VIDEO_TYPES: Set[str] = {
    "video/mp4",
    "video/quicktime",  # .mov
    "video/webm",
    "video/x-m4v",
    "video/m4v",
    "video/x-matroska",
    "video/avi",
    "video/x-msvideo",
}

ALLOWED_AUDIO_TYPES: Set[str] = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/m4a",
    "audio/x-m4a",
    "audio/aac",
    "audio/ogg",
    "audio/webm",
}

# Standard file extensions mapped to content categories
IMAGE_EXTENSIONS = (
    ".jpg", ".jpeg", ".jpe", ".jfif", ".jif",
    ".png",
    ".webp",
    ".heic", ".heif", ".hif",
    ".bmp", ".dib",
    ".tiff", ".tif",
    ".avif",
    ".gif",
)

VIDEO_EXTENSIONS = (
    ".mp4", ".mov", ".webm", ".m4v", ".mkv", ".avi",
)

AUDIO_EXTENSIONS = (
    ".wav", ".wave", ".mp3", ".m4a", ".aac", ".ogg", ".webm",
)


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
    is_image_category = bool(allowed_types.intersection(ALLOWED_IMAGE_TYPES))
    is_video_category = bool(allowed_types.intersection(ALLOWED_VIDEO_TYPES))
    is_audio_category = bool(allowed_types.intersection(ALLOWED_AUDIO_TYPES))

    if is_image_category and filename_lower.endswith(IMAGE_EXTENSIONS):
        valid_ext = True
    if is_video_category and filename_lower.endswith(VIDEO_EXTENSIONS):
        valid_ext = True
    if is_audio_category and filename_lower.endswith(AUDIO_EXTENSIONS):
        valid_ext = True

    # Allow if exact MIME match OR if recognized extension accompanied by standard/generic media types
    is_generic_mime = raw_content_type in {
        "application/octet-stream",
        "binary/octet-stream",
        "image/*",
        "video/*",
        "audio/*",
        "",
    }

    if raw_content_type not in allowed_types and not (valid_ext and (is_generic_mime or raw_content_type.startswith(("image/", "video/", "audio/")))):
        logger.warning(
            "Rejected upload '%s' with invalid content-type: %s",
            upload_file.filename,
            upload_file.content_type,
        )
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported format for {label} ('{upload_file.content_type}'). "
                f"Supported image formats: JPEG (.jpg, .jpeg), PNG (.png), WebP (.webp), "
                f"HEIC/HEIF (.heic), BMP (.bmp), TIFF (.tif), AVIF (.avif)."
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

    content = b"".join(chunks)

    # 3. Magic-byte signature verification (defends against extension spoofing)
    if is_image_category:
        is_jpeg = content.startswith(b"\xff\xd8\xff")
        is_png = content.startswith(b"\x89PNG\r\n\x1a\n")
        is_webp = content.startswith(b"RIFF") and len(content) > 12 and content[8:12] == b"WEBP"
        is_bmp = content.startswith(b"BM")
        is_tiff = content.startswith(b"II*\x00") or content.startswith(b"MM\x00*")
        is_gif = content.startswith(b"GIF87a") or content.startswith(b"GIF89a")
        # ISO base media box (HEIC, HEIF, AVIF)
        is_isobmff = (
            len(content) > 12
            and content[4:8] == b"ftyp"
            and any(
                content[8:12].startswith(b)
                for b in (b"heic", b"heix", b"heim", b"heis", b"hevc", b"hevx", b"mif1", b"msf1", b"avif", b"avis")
            )
        )

        genuine_magic = is_jpeg or is_png or is_webp or is_bmp or is_tiff or is_gif or is_isobmff

        if not genuine_magic:
            # Fallback verification through Pillow header check
            try:
                import io
                from PIL import Image
                img = Image.open(io.BytesIO(content))
                img.verify()
                genuine_magic = True
            except Exception:
                genuine_magic = False

        if not genuine_magic:
            logger.warning("Rejected upload '%s': failed magic-byte header inspection", upload_file.filename)
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Security: File content does not match genuine image magic headers (JPEG/PNG/WebP/HEIC/BMP/TIFF/AVIF).",
            )
    elif "audio/wav" in allowed_types:
        is_wav = content.startswith(b"RIFF") and len(content) > 12 and content[8:12] == b"WAVE"
        is_mp3 = content.startswith(b"ID3") or (len(content) > 2 and content[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"))
        if not (is_wav or is_mp3):
            logger.warning("Rejected upload '%s': failed audio magic-byte inspection", upload_file.filename)
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Security: File content does not match standard RIFF/WAVE or MP3 audio format.",
            )

    return content
