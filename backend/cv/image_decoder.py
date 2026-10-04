"""
Universal Image Decoder Service.

Provides robust, multi-format image decoding with automatic EXIF orientation
correction. Supports standard consumer camera formats and modern mobile image
containers:
  - JPEG / JPG / JPE / JFIF
  - PNG / APNG
  - WebP
  - HEIC / HEIF / HIF (Apple iOS native format via pillow-heif)
  - BMP / DIB
  - TIFF / TIF
  - AVIF / AVIS
  - Static GIF frames

Converts all supported formats cleanly into standard 8-bit 3-channel OpenCV
BGR NumPy arrays (H, W, 3) ready for the downstream CV pipeline.
"""
from __future__ import annotations

import io
import logging
import numpy as np
import cv2
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# Register HEIF/HEIC decoder with Pillow if available
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    logger.debug("pillow_heif successfully registered for HEIC/HEIF decoding")
except ImportError:
    logger.debug("pillow_heif not installed; native HEIC decoding disabled")
except Exception as _heif_err:
    logger.warning("Failed to register pillow_heif: %s", _heif_err)


def decode_image_to_bgr(image_bytes: bytes) -> np.ndarray | None:
    """
    Decodes arbitrary image bytes into an 8-bit BGR OpenCV NumPy array.

    Handles:
      1. EXIF orientation transposition (ensuring mobile camera photos are right-side-up).
      2. Color mode normalization (RGBA with alpha transparency, grayscale L, CMYK, etc. -> RGB -> BGR).
      3. Format flexibility: JPEG, PNG, WebP, HEIC/HEIF, BMP, TIFF, AVIF, GIF.
      4. Resilient fallback to cv2.imdecode if PIL encountered an issue.

    Args:
        image_bytes: Raw binary bytes of the image file.

    Returns:
        np.ndarray of shape (H, W, 3) in BGR color order, or None if undecodable.
    """
    if not image_bytes or len(image_bytes) < 8:
        logger.error("decode_image_to_bgr: Empty or truncated image bytes (< 8 bytes)")
        return None

    # 1. Primary decoder: Pillow with EXIF transposition and color mode normalization
    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
        pil_img = ImageOps.exif_transpose(pil_img)

        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")

        rgb_arr = np.array(pil_img, dtype=np.uint8)
        if rgb_arr.ndim == 3 and rgb_arr.shape[2] == 3:
            bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
            return bgr_arr
    except Exception as pil_err:
        logger.debug("Pillow image decode failed (%s); trying OpenCV imdecode fallback", pil_err)

    # 2. Secondary fallback: OpenCV imdecode directly from raw buffer
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        bgr_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if bgr_cv is not None and bgr_cv.size > 0:
            return bgr_cv
    except Exception as cv_err:
        logger.debug("OpenCV imdecode failed (%s)", cv_err)

    logger.error("decode_image_to_bgr: Failed to decode image bytes with both Pillow and OpenCV")
    return None


def transcode_to_standard_jpeg(image_bytes: bytes, quality: int = 95) -> bytes:
    """
    Normalizes any image upload to standard baseline JPEG for universal
    web browser rendering, mobile webview display, and ReportLab PDF inclusion.

    If the bytes are already valid JPEG bytes, returns them unchanged without re-compression.

    Args:
        image_bytes: Raw binary image data.
        quality: JPEG compression quality (1-100, default 95).

    Returns:
        Binary bytes of a valid JPEG image.
    """
    if not image_bytes:
        return image_bytes

    # If already a valid JPEG, no transcoding needed
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return image_bytes

    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
        pil_img = ImageOps.exif_transpose(pil_img)
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")

        out_buf = io.BytesIO()
        pil_img.save(out_buf, format="JPEG", quality=quality, optimize=True)
        return out_buf.getvalue()
    except Exception as err:
        logger.warning("transcode_to_standard_jpeg: Fallback to raw bytes due to error: %s", err)
        return image_bytes
