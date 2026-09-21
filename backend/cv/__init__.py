"""CV package init."""
from cv.pipeline import PipelineResult, run_pipeline
from cv.quality_gate import QualityGateResult, check_image_quality

__all__ = [
    "run_pipeline",
    "PipelineResult",
    "check_image_quality",
    "QualityGateResult",
]
