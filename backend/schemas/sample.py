"""Pydantic schemas for Sample and OnionInstance API responses."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ── Sample schemas ─────────────────────────────────────────────────────────────

class SampleDetail(BaseModel):
    """Full sample detail including processing status and calibration results."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    inspection_id: str
    sample_index: int
    image_path: str | None
    processed_image_path: str | None
    original_image_url: str | None = None
    processed_image_url: str | None = None
    image_width_px: int | None
    image_height_px: int | None
    marker_detected: bool
    scale_mm_per_px: float | None
    perspective_valid: bool
    quality_passed: bool
    quality_flags: list[str] = Field(default_factory=list)
    processing_status: str
    processing_error: str | None
    processing_started_at: datetime | None
    processing_finished_at: datetime | None
    model_version: str | None
    geo_lat: float | None
    geo_lon: float | None
    location_accuracy_m: float | None
    created_at: datetime

    # Onion instance summaries (populated by service layer)
    onion_count: int = 0
    onion_instances: list["OnionInstanceSummary"] = Field(default_factory=list)

    # Post-harvest storage advisory & Mandi commercial settlement
    storage_advisory: dict | None = None
    commercial_settlement: dict | None = None


# ── OnionInstance schemas ──────────────────────────────────────────────────────

class OnionInstanceSummary(BaseModel):
    """Summary used in sample list and result grid."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    instance_index: int
    display_number: int                    # instance_index + 1
    bbox_x: int
    bbox_y: int
    bbox_w: int
    bbox_h: int
    segmentation_conf: float
    touches_border: bool

    # Flattened from child models for quick grid display
    equivalent_diameter_mm: float | None = None
    equatorial_diameter_mm: float | None = None
    polar_length_mm: float | None = None
    shape_class: str | None = None
    estimated_weight_grams: float | None = None
    mandi_size_grade: str | None = None
    damaged_prob: float | None = None
    rotten_prob: float | None = None
    sprouted_prob: float | None = None
    is_mock_defect: bool = True
    grade: str | None = None              # GRADE_A | URS | REJECTED | NEEDS_REVIEW
    confidence_tier: str | None = None    # HIGH | NEEDS_REVIEW | UNUSABLE
    storageability_score: float | None = None
    storage_tier: str | None = None

    # Image evidence URLs (constructed by service layer from paths)
    crop_url: str | None = None
    mask_url: str | None = None


class OnionInstanceDetail(BaseModel):
    """Full evidence drilldown for a single onion."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    instance_index: int
    display_number: int
    bbox_x: int
    bbox_y: int
    bbox_w: int
    bbox_h: int
    segmentation_conf: float
    touches_border: bool
    crop_url: str | None
    mask_url: str | None

    # Defect observation
    damaged_prob: float | None
    rotten_prob: float | None
    sprouted_prob: float | None
    defect_model_version: str | None
    is_mock_defect: bool
    has_human_correction: bool = False
    corrected_by: str | None = None
    morphology: dict = Field(default_factory=dict)

    # Post-harvest storage assessment
    storageability_score: float | None = None
    shelf_life_days_est: int | None = None
    storage_tier: str | None = None
    decay_risk_factors: list[str] = Field(default_factory=list)

    # Measurement
    equivalent_diameter_mm: float | None
    major_axis_mm: float | None
    minor_axis_mm: float | None
    equatorial_diameter_mm: float | None = None
    polar_length_mm: float | None = None
    shape_index: float | None = None
    shape_class: str | None = None
    estimated_weight_grams: float | None = None
    mandi_size_grade: str | None = None
    mask_area_px: int | None
    scale_mm_per_px: float | None
    projection_note: str | None
    uncertainty_flag: bool = False

    # Classification result
    grade: str | None
    rejection_reasons: list[str] = Field(default_factory=list)
    confidence_tier: str | None
    ruleset_version: str | None
    explanation: dict = Field(default_factory=dict)


class OnionCorrectionRequest(BaseModel):
    """Officer manual correction for a single onion's defect observation."""
    damaged_prob: float = Field(ge=0.0, le=1.0)
    rotten_prob: float = Field(ge=0.0, le=1.0)
    sprouted_prob: float = Field(ge=0.0, le=1.0)
    corrected_by: str = Field(min_length=1, max_length=100, description="Officer identifier")
    notes: str | None = None
