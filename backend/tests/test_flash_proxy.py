"""
Unit tests for Flash Proxy Index (FPI) differential reflectance module.
========================================================================
Covers:
- compute_flash_proxy_map (normalization, channel weighting, dimension alignment)
- analyze_bulb_fpi (healthy vs suspect cuticular tissue, small masks, empty inputs)
- generate_fpi_heatmap (colormap generation, masking)
- encode_heatmap_to_base64 (valid JPEG base64 strings)
- FLASH_PROXY_LIMITATION_STATEMENT validation
"""
from __future__ import annotations

import sys
from pathlib import Path
import cv2
import numpy as np
import pytest

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from cv.flash_proxy import (
    FLASH_PROXY_LIMITATION_STATEMENT,
    analyze_bulb_fpi,
    compute_flash_proxy_map,
    encode_heatmap_to_base64,
    generate_fpi_heatmap,
)


class TestFlashProxyComputation:
    """Tests for compute_flash_proxy_map."""

    def test_limitation_statement_is_honest(self):
        assert "laboratory NIR/SWIR spectroscopy" in FLASH_PROXY_LIMITATION_STATEMENT
        assert "non-destructive optical proxy" in FLASH_PROXY_LIMITATION_STATEMENT

    def test_identical_ambient_and_flash_produces_zero_fpi(self):
        img = np.full((100, 100, 3), 128, dtype=np.uint8)
        fpi = compute_flash_proxy_map(img, img)

        assert fpi.shape == (100, 100)
        assert np.allclose(fpi, 0.0)

    def test_flash_brighter_than_ambient_produces_positive_fpi(self):
        ambient = np.full((50, 50, 3), 50, dtype=np.uint8)
        flash = np.full((50, 50, 3), 150, dtype=np.uint8)
        fpi = compute_flash_proxy_map(ambient, flash)

        assert fpi.shape == (50, 50)
        assert np.all(fpi > 0.0)
        assert np.all(fpi <= 1.0)

    def test_dimension_mismatch_auto_resizes(self):
        ambient = np.full((120, 160, 3), 40, dtype=np.uint8)
        flash = np.full((240, 320, 3), 100, dtype=np.uint8)
        fpi = compute_flash_proxy_map(ambient, flash)

        assert fpi.shape == (120, 160)
        assert np.all(fpi > 0.0)

    def test_none_input_raises_value_error(self):
        img = np.full((50, 50, 3), 50, dtype=np.uint8)
        with pytest.raises(ValueError):
            compute_flash_proxy_map(None, img)


class TestBulbFpiAnalysis:
    """Tests for analyze_bulb_fpi."""

    def test_healthy_uniform_low_fpi_returns_normal(self):
        fpi_map = np.full((100, 100), 0.20, dtype=np.float32)
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 255

        result = analyze_bulb_fpi(fpi_map, mask)
        assert result.surface_state == "NORMAL"
        assert result.mean_fpi == pytest.approx(0.20, abs=0.01)
        assert result.lesion_area_ratio == 0.0
        assert result.confidence >= 0.80

    def test_high_mean_fpi_returns_suspect(self):
        # High overall differential reflectance
        fpi_map = np.full((100, 100), 0.55, dtype=np.float32)
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 255

        result = analyze_bulb_fpi(fpi_map, mask)
        assert result.surface_state == "SUSPECT"
        assert result.mean_fpi == pytest.approx(0.55, abs=0.01)

    def test_patchy_lesions_return_suspect(self):
        # Mostly low FPI, but localized patch > 0.45
        fpi_map = np.full((100, 100), 0.25, dtype=np.float32)
        fpi_map[40:60, 40:60] = 0.80  # 20x20 = 400 pixels
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 255  # 60x60 = 3600 pixels (patch is ~11% > 0.45)

        # Make patch slightly larger to cross 12% threshold
        fpi_map[35:65, 35:65] = 0.85

        result = analyze_bulb_fpi(fpi_map, mask)
        assert result.surface_state == "SUSPECT"
        assert result.lesion_area_ratio > 0.12

    def test_tiny_mask_returns_invalid(self):
        fpi_map = np.full((100, 100), 0.20, dtype=np.float32)
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[10:12, 10:12] = 255  # only 4 pixels

        result = analyze_bulb_fpi(fpi_map, mask)
        assert result.surface_state == "INVALID"
        assert result.confidence == 0.0


class TestHeatmapAndEncoding:
    """Tests for generate_fpi_heatmap and base64 encoding."""

    def test_generate_heatmap_shape_and_type(self):
        fpi_map = np.linspace(0.0, 1.0, 10000).reshape((100, 100)).astype(np.float32)
        heatmap = generate_fpi_heatmap(fpi_map)

        assert heatmap.shape == (100, 100, 3)
        assert heatmap.dtype == np.uint8

    def test_generate_masked_heatmap(self):
        fpi_map = np.full((100, 100), 0.5, dtype=np.float32)
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[25:75, 25:75] = 255

        masked_heatmap = generate_fpi_heatmap(fpi_map, bulb_mask=mask)
        # Outside mask should be black
        assert np.all(masked_heatmap[0, 0] == [0, 0, 0])
        # Inside mask should have color
        assert np.any(masked_heatmap[50, 50] > 0)

    def test_encode_heatmap_to_base64_valid(self):
        img = np.full((50, 50, 3), 120, dtype=np.uint8)
        b64 = encode_heatmap_to_base64(img)

        assert isinstance(b64, str)
        assert len(b64) > 100


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app) as test_client:
        yield test_client


class TestFlashProxyApiEndpoint:
    """Integration tests for POST /api/v1/inspections/{id}/fpi endpoint."""

    def test_fpi_endpoint_success(self, client):
        # 1. Create inspection
        create_resp = client.post(
            "/api/v1/inspections",
            json={
                "lot_id": "LOT-FPI-TEST-01",
                "procurement_centre": "Kalwan APMC Mandi",
            },
        )
        assert create_resp.status_code == 201
        insp_id = create_resp.json()["id"]

        # 2. Generate synthetic ambient and flash image bytes
        amb_img = np.full((120, 160, 3), 70, dtype=np.uint8)
        flash_img = np.full((120, 160, 3), 140, dtype=np.uint8)

        _, amb_bytes = cv2.imencode(".jpg", amb_img)
        _, flash_bytes = cv2.imencode(".jpg", flash_img)

        # 3. Call FPI endpoint
        files = {
            "ambient_file": ("amb.jpg", amb_bytes.tobytes(), "image/jpeg"),
            "flash_file": ("flash.jpg", flash_bytes.tobytes(), "image/jpeg"),
        }
        resp = client.post(f"/api/v1/inspections/{insp_id}/fpi", files=files)
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "success"
        assert data["inspection_id"] == insp_id
        assert "mean_fpi" in data
        assert data["surface_state"] in ("NORMAL", "SUSPECT")
        assert len(data["heatmap_base64"]) > 50
        assert "spectroscopy" in data["limitation_statement"]

    def test_fpi_endpoint_not_found(self, client):
        files = {
            "ambient_file": ("amb.jpg", b"fake", "image/jpeg"),
            "flash_file": ("flash.jpg", b"fake", "image/jpeg"),
        }
        resp = client.post("/api/v1/inspections/00000000-0000-0000-0000-000000000000/fpi", files=files)
        assert resp.status_code == 404

