"""
YOLO11 segmentation provider.

Uses Ultralytics YOLO11-seg for instance segmentation of onion bulbs.
Model is loaded once at startup and reused across all requests.
Inference runs in a thread pool (see pipeline.py) to avoid blocking
the FastAPI async event loop.

License note: Ultralytics YOLO11 is AGPL-3.0. This is acceptable for
an open-source hackathon project. For any closed commercial use, an
Ultralytics Enterprise License is required.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np

from cv.providers.base import OnionDetection, SegmentationProvider, SegmentationResult

logger = logging.getLogger(__name__)

# Lazy import: only import ultralytics when this provider is actually used.
# This allows the application to start without ultralytics/torch installed
# (the mock provider will be used instead).
try:
    from ultralytics import YOLO as _YOLO
    _ULTRALYTICS_AVAILABLE = True
except ImportError:
    _YOLO = None  # type: ignore[assignment]
    _ULTRALYTICS_AVAILABLE = False


class YOLO11SegmentationProvider(SegmentationProvider):
    """
    YOLO11-seg instance segmentation provider.

    Preferred model: yolo11s-seg (small, 20 MB) — better occlusion handling
    via C2PSA spatial attention than yolo11n-seg.

    CPU fallback: yolo11n-seg (nano, 6 MB) — faster on CPU-only machines.
    """

    def __init__(
        self,
        model_path: str | Path,
        conf_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        device: str = "cpu",
    ) -> None:
        self._model_path = Path(model_path)
        self._conf = conf_threshold
        self._iou = iou_threshold
        self._device = device
        self._model = None
        self._version_str: str = "yolo11-seg:not_loaded"
        self._load_model()

    def _load_model(self) -> None:
        if not _ULTRALYTICS_AVAILABLE:
            logger.error("ultralytics not installed — YOLO11 provider cannot load.")
            return
        if not self._model_path.exists():
            logger.warning(
                "YOLO11 model weights not found at %s. "
                "Run: python -c \"from ultralytics import YOLO; YOLO('yolo11n-seg.pt')\" "
                "to download. Using mock provider until weights are available.",
                self._model_path,
            )
            return
        try:
            self._model = _YOLO(str(self._model_path))
            # Ultralytics version is embedded in the model metadata after loading
            import ultralytics
            self._version_str = (
                f"yolo11-seg:{self._model_path.stem}:{ultralytics.__version__}"
            )
            logger.info("YOLO11 model loaded from %s", self._model_path)
        except Exception:
            logger.exception("Failed to load YOLO11 model from %s", self._model_path)
            self._model = None

    @property
    def model_version(self) -> str:
        return self._version_str

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def detect(self, image: np.ndarray) -> SegmentationResult:
        """
        Run YOLO11-seg on the given BGR image.

        Returns empty SegmentationResult if the model is not loaded.
        Never raises — all exceptions are caught and logged.
        """
        if not self.is_ready:
            logger.warning("YOLO11 model not ready, returning empty detections")
            return SegmentationResult(provider_name="yolo11", model_version=self._version_str)

        start = time.perf_counter()
        try:
            results = self._model.predict(
                source=image,
                conf=self._conf,
                iou=self._iou,
                device=self._device,
                verbose=False,
            )
        except Exception:
            logger.exception("YOLO11 inference failed")
            return SegmentationResult(provider_name="yolo11", model_version=self._version_str)

        elapsed_ms = (time.perf_counter() - start) * 1000
        result = results[0]  # single-image prediction

        detections: list[OnionDetection] = []

        if result.masks is None or len(result.masks) == 0:
            return SegmentationResult(
                detections=[],
                provider_name="yolo11",
                model_version=self._version_str,
                inference_time_ms=elapsed_ms,
            )

        h, w = image.shape[:2]
        boxes = result.boxes
        masks_data = result.masks.data  # (N, H, W) float32 tensor 0-1

        for idx in range(len(boxes)):
            # Bounding box: xyxy format → convert to xywh
            x1, y1, x2, y2 = boxes.xyxy[idx].tolist()
            bbox_x = int(x1)
            bbox_y = int(y1)
            bbox_w = int(x2 - x1)
            bbox_h = int(y2 - y1)
            conf = float(boxes.conf[idx])

            # Convert mask from model output space to image space
            # masks_data is already resized to match the input image by ultralytics
            import cv2
            mask_float = masks_data[idx].cpu().numpy()  # (H_out, W_out) float32
            # Resize mask to match input image dimensions
            mask_resized = cv2.resize(mask_float, (w, h), interpolation=cv2.INTER_LINEAR)
            binary_mask = (mask_resized > 0.5).astype(np.uint8) * 255

            # Detect border touch
            touches_border = bool(
                binary_mask[0, :].any()
                or binary_mask[-1, :].any()
                or binary_mask[:, 0].any()
                or binary_mask[:, -1].any()
            )

            detections.append(
                OnionDetection(
                    bbox_x=bbox_x,
                    bbox_y=bbox_y,
                    bbox_w=bbox_w,
                    bbox_h=bbox_h,
                    mask=binary_mask,
                    confidence=conf,
                    touches_border=touches_border,
                    instance_index=idx,
                )
            )

        return SegmentationResult(
            detections=detections,
            provider_name="yolo11",
            model_version=self._version_str,
            inference_time_ms=elapsed_ms,
        )
