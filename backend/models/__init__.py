"""
SQLAlchemy ORM models package.

Import all models here so that:
1. `database.create_all_tables()` picks them up via metadata.
2. Alembic's `env.py` can see all models for migration generation.
"""
from models.inspection import Inspection
from models.sample import Sample
from models.onion_instance import OnionInstance
from models.defect_observation import DefectObservation
from models.measurement import Measurement
from models.classification_result import ClassificationResult
from models.report import Report

__all__ = [
    "Inspection",
    "Sample",
    "OnionInstance",
    "DefectObservation",
    "Measurement",
    "ClassificationResult",
    "Report",
]
