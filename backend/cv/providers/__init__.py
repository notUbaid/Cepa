"""Providers package init."""
from cv.providers.base import OnionDetection, SegmentationProvider, SegmentationResult
from cv.providers.mock_provider import MockSegmentationProvider
from cv.providers.watershed_provider import WatershedSegmentationProvider
from cv.providers.yolo11_provider import YOLO11SegmentationProvider

__all__ = [
    "SegmentationProvider",
    "SegmentationResult",
    "OnionDetection",
    "YOLO11SegmentationProvider",
    "WatershedSegmentationProvider",
    "MockSegmentationProvider",
]
