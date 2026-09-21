"""
Mock segmentation provider for testing and demo fallback.

Generates DETERMINISTIC fake detections based on a hash of the input image.
This means the same image always produces the same mock result — critical for
reproducible demo testing.

IMPORTANT: This provider NEVER produces real CV results.
All detection results are clearly marked is_mock=True in the database.
The demo UI must visually distinguish MOCK results from real inference.

Use cases:
1. Unit and integration tests (no model weights required)
2. Demo fallback when model weights are not yet trained
3. Development without GPU

When mock is active, the API health endpoint reports:
  {"cv_status": "MOCK_MODE", "warning": "Defect classifier using mock predictions"}
"""
from __future__ import annotations

import hashlib
import logging

import numpy as np

from cv.providers.base import OnionDetection, SegmentationProvider, SegmentationResult

logger = logging.getLogger(__name__)

# Realistic onion size range for mock bboxes (fraction of image size)
_MOCK_ONION_SIZE_FRACTION_RANGE = (0.04, 0.12)
# Number of mock onions to generate per image
_MOCK_ONION_COUNT_RANGE = (8, 16)


class MockSegmentationProvider(SegmentationProvider):
    """
    Deterministic mock segmentation provider.

    Generates synthetic onion detections at reproducible positions
    using the image content hash as a random seed.
    """

    @property
    def model_version(self) -> str:
        return "mock-provider:v1"

    @property
    def is_ready(self) -> bool:
        return True  # Always ready — no weights required

    def detect(self, image: np.ndarray) -> SegmentationResult:
        h, w = image.shape[:2]

        # Derive a deterministic seed from image content
        # Using first 1000 bytes of the image to avoid hashing the entire image
        img_bytes = image.tobytes()[:1000]
        seed = int(hashlib.md5(img_bytes).hexdigest()[:8], 16) % (2**31)
        rng = np.random.RandomState(seed)

        n_onions = int(rng.randint(_MOCK_ONION_COUNT_RANGE[0], _MOCK_ONION_COUNT_RANGE[1]))
        detections: list[OnionDetection] = []

        for idx in range(n_onions):
            # Generate a realistic bbox
            size_frac = rng.uniform(*_MOCK_ONION_SIZE_FRACTION_RANGE)
            onion_w = max(30, int(min(w, h) * size_frac))
            onion_h = max(30, int(onion_w * rng.uniform(0.85, 1.15)))  # slightly elliptical

            # Random position, ensuring bbox stays within image
            x = int(rng.randint(10, max(11, w - onion_w - 10)))
            y = int(rng.randint(10, max(11, h - onion_h - 10)))

            # Generate a circular/elliptical mask
            mask = np.zeros((h, w), dtype=np.uint8)
            cx, cy = x + onion_w // 2, y + onion_h // 2
            # Use ellipse to approximate onion shape
            import cv2
            cv2.ellipse(
                mask,
                (cx, cy),
                (onion_w // 2, onion_h // 2),
                angle=float(rng.randint(0, 180)),
                startAngle=0,
                endAngle=360,
                color=255,
                thickness=-1,
            )

            conf = float(rng.uniform(0.45, 0.95))
            touches_border = (
                x <= 2 or y <= 2 or x + onion_w >= w - 2 or y + onion_h >= h - 2
            )

            detections.append(
                OnionDetection(
                    bbox_x=x,
                    bbox_y=y,
                    bbox_w=onion_w,
                    bbox_h=onion_h,
                    mask=mask,
                    confidence=conf,
                    touches_border=touches_border,
                    instance_index=idx,
                )
            )

        logger.debug("MockSegmentationProvider generated %d detections", len(detections))
        return SegmentationResult(
            detections=detections,
            provider_name="mock",
            model_version="mock-provider:v1",
            inference_time_ms=5.0,  # realistic-looking mock timing
        )
