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
except (ImportError, OSError, Exception):
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
        conf_threshold: float = 0.25,
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

        effective_conf = max(0.20, self._conf)
        effective_iou = self._iou
        target_classes_list = list(self._target_class_ids)
        
        # If we couldn't find any valid target classes, do not fall back to None (which detects EVERYTHING)
        if not target_classes_list:
            logger.warning("No target classes configured for YOLO11. Skipping inference to prevent garbage detections.")
            return SegmentationResult(provider_name="yolo11", model_version=self._version_str)

        try:
            results = self._model.predict(
                source=image,
                conf=effective_conf,
                iou=effective_iou,
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

        # Filter and rank candidate boxes
        candidate_indices = []
        for idx in range(len(boxes)):
            cls_id = int(boxes.cls[idx])
            if self._target_class_ids and cls_id not in self._target_class_ids:
                continue
            conf = float(boxes.conf[idx])
            if conf < effective_conf:
                continue
            candidate_indices.append(idx)

        candidate_indices.sort(key=lambda i: float(boxes.conf[i]), reverse=True)

        # Duplicate & containment suppression (suppress redundant nested/overlap boxes, flaps, hands)
        kept_indices = []
        for idx in candidate_indices:
            x1, y1, x2, y2 = boxes.xyxy[idx].tolist()
            area = max(1.0, (x2 - x1) * (y2 - y1))
            is_dup = False
            for k in kept_indices:
                kx1, ky1, kx2, ky2 = boxes.xyxy[k].tolist()
                k_area = max(1.0, (kx2 - kx1) * (ky2 - ky1))
                ix1, iy1 = max(x1, kx1), max(y1, ky1)
                ix2, iy2 = min(x2, kx2), min(y2, ky2)
                if ix2 > ix1 and iy2 > iy1:
                    inter = (ix2 - ix1) * (iy2 - iy1)
                    union = area + k_area - inter
                    iou = inter / max(1.0, union)
                    containment = inter / min(area, k_area)
                    if iou > 0.50 or containment > 0.70:
                        is_dup = True
                        break
            if not is_dup:
                kept_indices.append(idx)

        for idx in kept_indices:
            conf = float(boxes.conf[idx])
            x1, y1, x2, y2 = boxes.xyxy[idx].tolist()
            bbox_x = max(0, int(x1))
            bbox_y = max(0, int(y1))
            bbox_w = min(w - bbox_x, int(x2 - x1))
            bbox_h = min(h - bbox_y, int(y2 - y1))

            if bbox_w < 25 or bbox_h < 25:
                continue

            # Edge sliver guard: reject small fragments cut off by the camera frame edge
            touches_edge = (bbox_x <= 2 or bbox_y <= 2 or bbox_x + bbox_w >= w - 2 or bbox_y + bbox_h >= h - 2)
            if touches_edge and (min(bbox_w, bbox_h) < 30 or (bbox_w * bbox_h) < 1200):
                logger.debug("Filtered out edge sliver: %s", (bbox_x, bbox_y, bbox_w, bbox_h))
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

            # Produce Organic Chroma Gate (evaluated on mask pixels only, not the full bbox):
            # Allium bulbs may be:
            #   (a) Red/purple/golden — warm hue (0-35° or 145-180°) + moderate saturation
            #   (b) White/cream/silver — very high brightness (V > 160) + low saturation (S < 60)
            # Reject only clearly non-organic objects: dark electronic surfaces
            # (keyboards, monitors, desks) which are uniformly low-value AND achromatic.
            mask_crop = image[bbox_y : bbox_y + bbox_h, bbox_x : bbox_x + bbox_w]
            mask_roi  = binary_mask[bbox_y : bbox_y + bbox_h, bbox_x : bbox_x + bbox_w]
            if mask_crop.size > 0 and np.any(mask_roi > 0):
                hsv_cand = cv2.cvtColor(mask_crop, cv2.COLOR_BGR2HSV)
                hc, sc, vc = hsv_cand[:, :, 0], hsv_cand[:, :, 1], hsv_cand[:, :, 2]
                obj_bool = mask_roi > 0  # boolean mask of object pixels
                # Warm-pigmented onion pixels (red/purple/golden/yellow)
                warm_mask = ((hc < 35) | (hc > 145)) & (sc > 30) & (vc > 40) & (vc < 252)
                # White/cream onion pixels (high value, low-to-medium saturation)
                white_mask = (vc > 160) & (sc < 80)
                organic_in_obj = (warm_mask | white_mask) & obj_bool
                chroma_ratio = float(np.sum(organic_in_obj)) / max(1, float(np.sum(obj_bool)))
                if chroma_ratio < 0.15:
                    logger.debug(
                        "Filtered out non-organic detection via mask chroma gate (organic=%.2f): %s",
                        chroma_ratio, (bbox_x, bbox_y, bbox_w, bbox_h)
                    )
                    continue


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
