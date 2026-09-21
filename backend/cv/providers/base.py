"""
CV pipeline providers base class.

Defines the abstract interface for instance segmentation providers.
All concrete implementations (YOLO11, mock, future alternatives) must
implement this interface. This allows swapping the segmentation model
without changing any downstream pipeline code.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np


@dataclass
class OnionDetection:
    """
    Result of detecting and segmenting a single onion instance.

    All coordinates are in the image space passed to `detect()`.
    After homography rectification, these are in the rectified image space.
    """

    # Bounding box (x, y, width, height) in integer pixels
    bbox_x: int
    bbox_y: int
    bbox_w: int
    bbox_h: int

    # Binary segmentation mask: uint8 array, same HxW as input image.
    # 255 = onion, 0 = background.
    mask: np.ndarray

    # Detection confidence from the segmentation model [0, 1]
    confidence: float

    # Whether any mask pixel touches the image border
    # (set by pipeline after detection, not by the provider)
    touches_border: bool = False

    # Internal unique index within this detection batch (set by pipeline)
    instance_index: int = 0

    @property
    def mask_area_px(self) -> int:
        """Number of pixels in the segmentation mask."""
        return int(np.count_nonzero(self.mask))

    @property
    def bbox_center(self) -> tuple[float, float]:
        return (self.bbox_x + self.bbox_w / 2, self.bbox_y + self.bbox_h / 2)


@dataclass
class SegmentationResult:
    """
    Full output of a segmentation provider for one image.
    """
    detections: list[OnionDetection] = field(default_factory=list)
    # Provider-specific info for logging / debugging
    provider_name: str = ""
    model_version: str = ""
    # Raw inference time (milliseconds, measured by provider)
    inference_time_ms: float = 0.0

    @property
    def count(self) -> int:
        return len(self.detections)


class SegmentationProvider(ABC):
    """
    Abstract base class for instance segmentation providers.

    Implement this to plug in any segmentation model.
    The pipeline code depends only on this interface.
    """

    @property
    @abstractmethod
    def model_version(self) -> str:
        """
        Human-readable model identifier string.
        Stored with every result for traceability.
        Example: "yolo11s-seg:8.4.157"
        """
        ...

    @property
    @abstractmethod
    def is_ready(self) -> bool:
        """True if the model is loaded and ready for inference."""
        ...

    @abstractmethod
    def detect(self, image: np.ndarray) -> SegmentationResult:
        """
        Run instance segmentation on the given image.

        Args:
            image: BGR uint8 numpy array (OpenCV convention).
                   Expected to be the perspective-corrected (rectified) image.

        Returns:
            SegmentationResult with detected onion instances.
            Returns empty SegmentationResult (no detections) on failure —
            never raises exceptions that would crash the pipeline.
        """
        ...
