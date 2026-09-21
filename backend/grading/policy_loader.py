"""
Grading Policy Loader

Loads and validates YAML policy files from the policies directory.
Policy files define the procurement grading thresholds and rules.

Design principle: All procurement business rules live in YAML files,
NOT in application code. This means:
  - Rules can be updated without code changes or redeployment
  - The active policy version is always visible and traceable
  - DEMO assumptions are clearly separated from verified specifications
  - Future NAFED-verified rules can be added as new YAML files

Policy format is validated against a strict schema on load.
An invalid policy file causes a startup error, not a silent bad grade.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class SizeThresholds:
    grade_a_min_mm: float
    grade_a_max_mm: float
    urs_min_mm: float
    urs_max_mm: float

    @property
    def all_thresholds(self) -> list[float]:
        """All boundary values — used for uncertainty flagging."""
        return [self.grade_a_min_mm, self.grade_a_max_mm, self.urs_min_mm, self.urs_max_mm]


@dataclass
class DefectThresholds:
    damaged_threshold: float    # prob above this = DAMAGED
    rotten_threshold: float     # prob above this = ROTTEN
    sprouted_threshold: float   # prob above this = SPROUTED


@dataclass
class ReviewThresholds:
    size_tolerance_mm: float           # mm margin that triggers NEEDS_REVIEW
    defect_prob_range: tuple[float, float]  # (low, high) for borderline range


@dataclass
class GradingPolicy:
    """Fully parsed and validated procurement grading policy."""

    version: str
    label: str
    source_note: str
    verified: bool             # False for DEMO_ASSUMPTION, True for official specs
    urs_active: bool           # Whether the URS category is currently active

    size: SizeThresholds
    defect: DefectThresholds
    review: ReviewThresholds

    grade_a_rules: dict        # raw YAML rules block
    urs_rules: dict
    hard_rejection: dict
    rejection_reason_codes: list[str] = field(default_factory=list)


def load_policy(version: str, policies_dir: Path) -> GradingPolicy:
    """
    Load and parse a grading policy YAML file by version name.

    Args:
        version: Policy version string, e.g. "DEMO_ASSUMPTION_v1"
        policies_dir: Directory containing .yaml policy files.

    Returns:
        GradingPolicy ready for use by the grading engine.

    Raises:
        FileNotFoundError: If the policy file doesn't exist.
        ValueError: If the policy file is malformed or missing required fields.
    """
    policy_path = policies_dir / f"{version}.yaml"

    if not policy_path.exists():
        raise FileNotFoundError(
            f"Grading policy '{version}' not found at {policy_path}. "
            f"Available policies: {list(policies_dir.glob('*.yaml'))}"
        )

    with policy_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError(f"Policy file {policy_path} must be a YAML mapping, got {type(raw)}")

    try:
        size_raw = raw["size"]
        defect_raw = raw["defect_thresholds"]
        review_raw = raw.get("review_thresholds", {})

        policy = GradingPolicy(
            version=str(raw["version"]),
            label=str(raw.get("label", "")),
            source_note=str(raw.get("source_note", "")),
            verified=bool(raw.get("verified", False)),
            urs_active=bool(raw.get("urs_active", True)),
            size=SizeThresholds(
                grade_a_min_mm=float(size_raw["grade_a_min_mm"]),
                grade_a_max_mm=float(size_raw["grade_a_max_mm"]),
                urs_min_mm=float(size_raw["urs_min_mm"]),
                urs_max_mm=float(size_raw["urs_max_mm"]),
            ),
            defect=DefectThresholds(
                damaged_threshold=float(defect_raw["damaged_threshold"]),
                rotten_threshold=float(defect_raw["rotten_threshold"]),
                sprouted_threshold=float(defect_raw["sprouted_threshold"]),
            ),
            review=ReviewThresholds(
                size_tolerance_mm=float(review_raw.get("size_tolerance_mm", 3.0)),
                defect_prob_range=(
                    float(review_raw.get("defect_prob_range", [0.35, 0.65])[0]),
                    float(review_raw.get("defect_prob_range", [0.35, 0.65])[1]),
                ),
            ),
            grade_a_rules=raw.get("grade_a_rules", {}),
            urs_rules=raw.get("urs_rules", {}),
            hard_rejection=raw.get("hard_rejection", {}),
            rejection_reason_codes=list(raw.get("rejection_reason_codes", [])),
        )
    except KeyError as e:
        raise ValueError(
            f"Policy file {policy_path} is missing required field: {e}"
        ) from e
    except (TypeError, ValueError) as e:
        raise ValueError(f"Policy file {policy_path} has invalid value: {e}") from e

    # Validate logical consistency of size thresholds
    if policy.size.urs_min_mm > policy.size.grade_a_min_mm:
        raise ValueError(
            f"Policy {version}: urs_min_mm ({policy.size.urs_min_mm}) must be "
            f"<= grade_a_min_mm ({policy.size.grade_a_min_mm})"
        )
    if policy.size.grade_a_max_mm > policy.size.urs_max_mm:
        raise ValueError(
            f"Policy {version}: grade_a_max_mm ({policy.size.grade_a_max_mm}) must be "
            f"<= urs_max_mm ({policy.size.urs_max_mm})"
        )

    if not policy.verified:
        logger.warning(
            "Grading policy '%s' is NOT officially verified (%s). "
            "Results are based on demo assumptions.",
            version, policy.source_note,
        )

    logger.info(
        "Loaded grading policy '%s' (verified=%s, urs_active=%s)",
        version, policy.verified, policy.urs_active,
    )
    return policy
