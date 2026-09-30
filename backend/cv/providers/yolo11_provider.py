"""
YOLO11 segmentation provider.

Uses Ultralytics YOLO11-seg for instance segmentation of onion bulbs.
Model is loaded once at startup and reused across all requests.
Inference runs in a thread pool (see pipeline.py) to avoid blocking
the FastAPI async event loop.

Enhanced with:
  1. Dynamic class awareness (supports custom fine-tuned 'onion' class and COCO proxy classes).
  2. Dual-confidence recovery (retains borderline detections with convex globular morphology).
  3. Morphological mask refinement (seals specular highlights and dry tunic cracks).
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import cv2
import numpy as np

from cv.providers.base import OnionDetection, SegmentationProvider, SegmentationResult

logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO as _YOLO
    _ULTRALYTICS_AVAILABLE = True
except ImportError:
    _YOLO = None  # type: ignore[assignment]
    _ULTRALYTICS_AVAILABLE = False


class YOLO11SegmentationProvider(SegmentationProvider):
    """
    YOLO11-seg instance segmentation provider.

    Preferred model: yolo11s-seg (small, 20 MB) or fine-tuned yolo11n-seg.
    CPU fallback: yolo11n-seg (nano, 6 MB) for low-latency CPU operation.
    """

    def __init__(
        self,
        model_path: str | Path,
        conf_threshold: float = 0.30,
        iou_threshold: float = 0.45,
        device: str = "cpu",
    ) -> None:
        self._model_path = Path(model_path)
        self._conf = conf_threshold
        self._iou = iou_threshold
        self._device = device
        self._model = None
        self._version_str: str = "yolo11-seg:not_loaded"
        self._target_class_ids: set[int] = set()
        self._load_model()

    def _load_model(self) -> None:
        if not _ULTRALYTICS_AVAILABLE:
            logger.error("ultralytics not installed - YOLO11 provider cannot load.")
            return
        if not self._model_path.exists():
            # Try alternate fallback weights path
            fallback_path = self._model_path.parent / "yolo11n-seg-coco.pt"
            if fallback_path.exists():
                logger.info("Primary weights %s not found; falling back to %s", self._model_path, fallback_path)
                self._model_path = fallback_path
            else:
                logger.warning("YOLO11 model weights not found at %s.", self._model_path)
                return

        try:
            self._model = _YOLO(str(self._model_path))
            import ultralytics
            self._version_str = (
                f"yolo11-seg:{self._model_path.stem}:{ultralytics.__version__}"
            )

            # Detect class schema
            names = getattr(self._model, "names", {})
            if isinstance(names, dict):
                onion_ids = {k for k, v in names.items() if "onion" in str(v).lower()}
                if onion_ids:
                    self._target_class_ids = onion_ids
                    logger.info("Loaded custom onion segmentation weights (classes: %s)", self._target_class_ids)
                else:
                    # COCO pretrained fallback: strictly restrict to circular produce items only
                    # Never allow person (class 0 in COCO), clothing, sacks, hands, or background objects
                    proxy_classes = {"apple", "orange"}
                    self._target_class_ids = {k for k, v in names.items() if str(v).lower() in proxy_classes}
                    logger.warning("Loaded COCO weights without onion class. Restricted to produce proxies: %s", self._target_class_ids)
            else:
                self._target_class_ids = {0}

            logger.info("YOLO11 model loaded from %s (target classes: %s)", self._model_path, self._target_class_ids)
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
        Run YOLO11-seg on the given BGR image with morphological mask refinement.
        Strictly segments only target onion/produce classes.
        """
        if not self.is_ready:
            logger.warning("YOLO11 model not ready, returning empty detections")
            return SegmentationResult(provider_name="yolo11", model_version=self._version_str)

        start = time.perf_counter()
        h, w = image.shape[:2]
        if h < 20 or w < 20:
            return SegmentationResult(provider_name="yolo11", model_version=self._version_str)

        # Sensitive base threshold for dual-confidence recovery
        base_conf = min(0.20, self._conf)
        target_classes_list = list(self._target_class_ids) if self._target_class_ids else None

        try:
            results = self._model.predict(
                source=image,
                conf=base_conf,
                iou=self._iou,
                classes=target_classes_list,
                device=self._device,
                verbose=False,
            )
        except Exception:
            logger.exception("YOLO11 inference failed")
            return SegmentationResult(provider_name="yolo11", model_version=self._version_str)

        elapsed_ms = (time.perf_counter() - start) * 1000
        result = results[0]

        detections: list[OnionDetection] = []

        if result.masks is None or len(result.masks) == 0:
            return SegmentationResult(
                detections=[],
                provider_name="yolo11",
                model_version=self._version_str,
                inference_time_ms=elapsed_ms,
            )

        boxes = result.boxes
        masks_data = result.masks.data
        close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

        for idx in range(len(boxes)):
            cls_id = int(boxes.cls[idx])
            if self._target_class_ids and cls_id not in self._target_class_ids:
                continue

            conf = float(boxes.conf[idx])
            x1, y1, x2, y2 = boxes.xyxy[idx].tolist()
            bbox_x = max(0, int(x1))
            bbox_y = max(0, int(y1))
            bbox_w = min(w - bbox_x, int(x2 - x1))
            bbox_h = min(h - bbox_y, int(y2 - y1))

            if bbox_w < 15 or bbox_h < 15:
                continue

            # Mask extraction and scaling
            mask_float = masks_data[idx].cpu().numpy()
            mask_resized = cv2.resize(mask_float, (w, h), interpolation=cv2.INTER_LINEAR)
            binary_mask = (mask_resized > 0.50).astype(np.uint8) * 255

            # Morphological mask refinement: seal specular reflection holes and dry tunic voids
            binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, close_kernel)
            cnts, hier = cv2.findContours(binary_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
            if hier is not None:
                for c_idx, h_info in enumerate(hier[0]):
                    if h_info[3] >= 0 and cv2.contourArea(cnts[c_idx]) < 10000:
                        cv2.drawContours(binary_mask, cnts, c_idx, 255, -1)

            # Dual-confidence geometric verification for borderline detections
            if conf < self._conf:
                mask_cnts, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if not mask_cnts:
                    continue
                c_max = max(mask_cnts, key=cv2.contourArea)
                c_area = cv2.contourArea(c_max)
                if c_area < 800:
                    continue
                hull = cv2.convexHull(c_max)
                hull_area = max(1.0, float(cv2.contourArea(hull)))
                solidity = float(c_area) / hull_area
                aspect_ratio = float(bbox_w) / max(1.0, float(bbox_h))

                # Borderline detections must have convex globular shape
                if solidity < 0.65 or aspect_ratio < 0.40 or aspect_ratio > 2.5:
                    logger.debug("Rejected borderline detection (conf=%.2f, sol=%.2f, ar=%.2f)", conf, solidity, aspect_ratio)
                    continue

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
                    instance_index=len(detections),
                )
            )

        return SegmentationResult(
            detections=detections,
            provider_name="yolo11",
            model_version=self._version_str,
            inference_time_ms=elapsed_ms,
        )
