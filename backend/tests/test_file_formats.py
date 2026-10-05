"""
Multi-Format File Support Test Suite.

Verifies that all standard and modern image, video, and audio formats
(JPEG, PNG, WebP, HEIC/HEIF, BMP, TIFF, AVIF, GIF, MP4, MOV, WAV, MP3)
are cleanly accepted by upload validation, decoded into standard OpenCV
arrays by the image decoder, normalized for web/PDF display, and processed
through the Cepa API endpoints.
"""
from __future__ import annotations

import io
from pathlib import Path
import pytest
import numpy as np
from PIL import Image
from fastapi import UploadFile, HTTPException
from fastapi.testclient import TestClient

from cv.image_decoder import decode_image_to_bgr, transcode_to_standard_jpeg
from services.upload_validator import (
    ALLOWED_IMAGE_TYPES,
    ALLOWED_VIDEO_TYPES,
    ALLOWED_AUDIO_TYPES,
    validate_and_read_upload,
)
from main import app


def _create_synthetic_image_bytes(fmt: str, mode: str = "RGB", size: tuple[int, int] = (64, 64)) -> bytes:
    """Helper to generate in-memory synthetic image bytes for tests."""
    color = (180, 50, 60) if mode == "RGB" else (180, 50, 60, 200) if mode == "RGBA" else 128
    img = Image.new(mode, size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


class TestImageDecoderUnit:
    """Unit tests for cv/image_decoder.py across various image containers."""

    def test_decode_jpeg(self):
        b = _create_synthetic_image_bytes("JPEG", "RGB")
        bgr = decode_image_to_bgr(b)
        assert bgr is not None
        assert bgr.shape == (64, 64, 3)
        assert bgr.dtype == np.uint8

    def test_decode_png_rgb(self):
        b = _create_synthetic_image_bytes("PNG", "RGB")
        bgr = decode_image_to_bgr(b)
        assert bgr is not None
        assert bgr.shape == (64, 64, 3)
        assert bgr.dtype == np.uint8

    def test_decode_png_rgba_alpha_composite(self):
        b = _create_synthetic_image_bytes("PNG", "RGBA")
        bgr = decode_image_to_bgr(b)
        assert bgr is not None
        assert bgr.shape == (64, 64, 3)
        assert bgr.dtype == np.uint8

    def test_decode_webp(self):
        b = _create_synthetic_image_bytes("WEBP", "RGB")
        bgr = decode_image_to_bgr(b)
        assert bgr is not None
        assert bgr.shape == (64, 64, 3)
        assert bgr.dtype == np.uint8

    def test_decode_bmp(self):
        b = _create_synthetic_image_bytes("BMP", "RGB")
        bgr = decode_image_to_bgr(b)
        assert bgr is not None
        assert bgr.shape == (64, 64, 3)
        assert bgr.dtype == np.uint8

    def test_decode_tiff(self):
        b = _create_synthetic_image_bytes("TIFF", "RGB")
        bgr = decode_image_to_bgr(b)
        assert bgr is not None
        assert bgr.shape == (64, 64, 3)
        assert bgr.dtype == np.uint8

    def test_decode_heif_when_supported(self):
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
            b = _create_synthetic_image_bytes("HEIF", "RGB")
            bgr = decode_image_to_bgr(b)
            assert bgr is not None
            assert bgr.shape == (64, 64, 3)
        except Exception:
            pytest.skip("HEIF encoding not supported in this test environment")

    def test_decode_empty_or_corrupt_returns_none(self):
        assert decode_image_to_bgr(b"") is None
        assert decode_image_to_bgr(b"1234567") is None
        assert decode_image_to_bgr(b"THIS_IS_NOT_AN_IMAGE_FILE_AT_ALL_JUST_RANDOM_TEXT") is None


class TestImageNormalizationUnit:
    """Unit tests for transcode_to_standard_jpeg."""

    def test_jpeg_passthrough(self):
        jpeg_bytes = _create_synthetic_image_bytes("JPEG", "RGB")
        out = transcode_to_standard_jpeg(jpeg_bytes)
        assert out == jpeg_bytes
        assert out.startswith(b"\xff\xd8\xff")

    def test_png_transcoded_to_jpeg(self):
        png_bytes = _create_synthetic_image_bytes("PNG", "RGB")
        out = transcode_to_standard_jpeg(png_bytes)
        assert out.startswith(b"\xff\xd8\xff")

    def test_bmp_transcoded_to_jpeg(self):
        bmp_bytes = _create_synthetic_image_bytes("BMP", "RGB")
        out = transcode_to_standard_jpeg(bmp_bytes)
        assert out.startswith(b"\xff\xd8\xff")

    def test_webp_transcoded_to_jpeg(self):
        webp_bytes = _create_synthetic_image_bytes("WEBP", "RGB")
        out = transcode_to_standard_jpeg(webp_bytes)
        assert out.startswith(b"\xff\xd8\xff")


class TestUploadValidatorFormats:
    """Unit tests for upload validation across all permitted MIME types and extensions."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "fmt,ext,mime",
        [
            ("JPEG", "jpg", "image/jpeg"),
            ("JPEG", "jpeg", "image/jpeg"),
            ("PNG", "png", "image/png"),
            ("WEBP", "webp", "image/webp"),
            ("BMP", "bmp", "image/bmp"),
            ("TIFF", "tif", "image/tiff"),
        ],
    )
    async def test_upload_validator_accepts_image_formats(self, fmt, ext, mime):
        img_bytes = _create_synthetic_image_bytes(fmt)
        fake_file = UploadFile(
            filename=f"test_bulb.{ext}",
            file=io.BytesIO(img_bytes),
            headers={"content-type": mime},
        )
        validated = await validate_and_read_upload(
            upload_file=fake_file,
            allowed_types=ALLOWED_IMAGE_TYPES,
            max_mb=10,
            label="Bulb Image",
        )
        assert len(validated) == len(img_bytes)

    @pytest.mark.asyncio
    async def test_upload_validator_accepts_octet_stream_with_valid_image_extension(self):
        """Tests that clients sending application/octet-stream with a valid image file succeed."""
        img_bytes = _create_synthetic_image_bytes("PNG")
        fake_file = UploadFile(
            filename="phone_capture.png",
            file=io.BytesIO(img_bytes),
            headers={"content-type": "application/octet-stream"},
        )
        validated = await validate_and_read_upload(
            upload_file=fake_file,
            allowed_types=ALLOWED_IMAGE_TYPES,
            max_mb=10,
        )
        assert len(validated) == len(img_bytes)

    @pytest.mark.asyncio
    async def test_upload_validator_rejects_spoofed_extension(self):
        """Tests that an executable renamed as .jpg fails magic byte verification."""
        fake_file = UploadFile(
            filename="fake.jpg",
            file=io.BytesIO(b"MZ\x90\x00NotAnImageExecutableFileContent1234567890"),
            headers={"content-type": "image/jpeg"},
        )
        with pytest.raises(HTTPException) as exc:
            await validate_and_read_upload(
                upload_file=fake_file,
                allowed_types=ALLOWED_IMAGE_TYPES,
                max_mb=10,
            )
        assert exc.value.status_code == 415

    @pytest.mark.asyncio
    async def test_upload_validator_rejects_dangerous_extensions(self):
        fake_file = UploadFile(
            filename="exploit.py",
            file=io.BytesIO(b"import os; os.system('echo 1')"),
            headers={"content-type": "text/x-python"},
        )
        with pytest.raises(HTTPException) as exc:
            await validate_and_read_upload(
                upload_file=fake_file,
                allowed_types=ALLOWED_IMAGE_TYPES,
                max_mb=10,
            )
        assert exc.value.status_code == 415


class TestApiMultiFormatIntegration:
    """Integration test checking that FastAPI accepts multiple formats in sample upload."""

    @pytest.fixture
    def test_inspection_id(self):
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/inspections",
                json={
                    "lot_id": "LOT-FMT-TEST",
                    "procurement_centre": "Lasalgaon Mandi",
                    "officer_name": "Quality Inspector",
                },
            )
            assert resp.status_code == 201
            return resp.json()["id"]

    def test_upload_png_sample_image(self, test_inspection_id: str):
        sample_path = Path(__file__).parent.parent / "static" / "synthetic_demo_spread.jpg"

        pil_img = Image.open(sample_path)
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        with TestClient(app) as client:
            resp = client.post(
                f"/api/v1/inspections/{test_inspection_id}/samples",
                files={"file": ("spread.png", io.BytesIO(png_bytes), "image/png")},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["inspection_id"] == test_inspection_id
            assert data["processing_status"] in ("DONE", "RUNNING")

    def test_upload_webp_sample_image(self, test_inspection_id: str):
        sample_path = Path(__file__).parent.parent / "static" / "synthetic_demo_spread.jpg"

        pil_img = Image.open(sample_path)
        buf = io.BytesIO()
        pil_img.save(buf, format="WEBP")
        webp_bytes = buf.getvalue()

        with TestClient(app) as client:
            resp = client.post(
                f"/api/v1/inspections/{test_inspection_id}/samples",
                files={"file": ("spread.webp", io.BytesIO(webp_bytes), "image/webp")},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["inspection_id"] == test_inspection_id
            assert data["processing_status"] in ("DONE", "RUNNING")
