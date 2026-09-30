"""
Automated database seeding service for ephemeral container hosting (e.g. Render).

When the backend boots on an ephemeral instance where the local SQLite database
was wiped, this service seeds a known-good, verified demo inspection complete with:
1. Static inspection ID matching the README API examples and curl commands.
2. Verified farmer details and 12-digit AgriStack Farmer ID.
3. Pre-generated report and share token for immediate public verification.
4. Auto-generated PDF voucher in storage.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models.inspection import Inspection
from models.sample import Sample
from models.onion_instance import OnionInstance
from models.measurement import Measurement
from models.defect_observation import DefectObservation
from models.classification_result import ClassificationResult
from models.report import Report
from services.report_generator import generate_pdf_report

logger = logging.getLogger(__name__)

DEMO_INSPECTION_ID = "c7a82e14-9b23-4e89-9a21-8f192a4b8e21"
DEMO_SAMPLE_ID = "e4b1029c-5a21-4f32-8e10-9c28174a6f23"
DEMO_REPORT_ID = "RPT-2026-DEMO-NASHIK-01"
DEMO_SHARE_TOKEN = "cepa-demo-share-token"


def seed_demo_data_if_empty() -> None:
    """Check if database is empty; if so, populate a verified demo inspection."""
    db: Session = SessionLocal()
    try:
        existing = db.query(Inspection).filter(
            (Inspection.id == DEMO_INSPECTION_ID) | (Inspection.lot_id == "LOT-NASHIK-RED-DEMO")
        ).first()

        if existing:
            logger.info("Demo inspection record exists (id=%s, lot=%s)", existing.id, existing.lot_id)
            return

        total_inspections = db.query(Inspection).count()
        if total_inspections > 0:
            logger.info("Database has %d existing inspections. Skipping seed.", total_inspections)
            return

        logger.info("Seeding initial demo inspection for ephemeral container startup...")

        now = datetime.now(timezone.utc)
        inspection = Inspection(
            id=DEMO_INSPECTION_ID,
            lot_id="LOT-NASHIK-RED-DEMO",
            procurement_centre="Lasalgaon APMC Mandi, Nashik",
            officer_name="Inspector Patil",
            officer_id="MH-NSK-104",
            farmer_name="Ramesh Patil",
            farmer_id="MH-NAS-2024-8842",
            status="FINALIZED",
            created_at=now,
            finalized_at=now,
            geo_lat=20.1458,
            geo_lon=74.2289,
            location_accuracy=4.2,
            notes="Demo calibration lot: Nashik Red cultivar spread under APMC standard intake protocol.",
        )
        db.add(inspection)
        db.flush()

        # Seed sample
        sample = Sample(
            id=DEMO_SAMPLE_ID,
            inspection_id=inspection.id,
            sample_index=1,
            image_path="demo_onion_spread.jpg",
            processed_image_path="demo_onion_spread.jpg",
            scale_mm_per_px=0.6836,
            perspective_valid=False,
            is_estimated_scale=True,
            calibration_method="AUTONOMOUS_OVERHEAD_HEURISTIC",
            created_at=now,
        )
        db.add(sample)
        db.flush()

        # Seed 20 representative bulb instances (16 Grade A, 3 URS, 1 Rejected)
        calipers = [
            (52.4, 50.1, 88.0, "GRADE_A", "SUPER", False, 0.05, 0.02, 0.01),
            (54.1, 52.0, 92.5, "GRADE_A", "SUPER", False, 0.04, 0.01, 0.01),
            (50.8, 48.5, 82.0, "GRADE_A", "SUPER", False, 0.02, 0.01, 0.01),
            (55.6, 53.2, 96.0, "GRADE_A", "SUPER", False, 0.03, 0.01, 0.02),
            (48.2, 46.0, 74.0, "GRADE_A", "SUPER", False, 0.06, 0.02, 0.01),
            (53.0, 51.2, 89.0, "GRADE_A", "SUPER", False, 0.02, 0.01, 0.01),
            (51.9, 49.8, 85.0, "GRADE_A", "SUPER", False, 0.04, 0.02, 0.01),
            (56.2, 54.0, 99.0, "GRADE_A", "SUPER", False, 0.05, 0.01, 0.01),
            (49.5, 47.2, 78.0, "GRADE_A", "SUPER", False, 0.03, 0.02, 0.01),
            (52.8, 50.5, 87.5, "GRADE_A", "SUPER", False, 0.02, 0.01, 0.01),
            (54.4, 52.1, 93.0, "GRADE_A", "SUPER", False, 0.04, 0.02, 0.02),
            (50.2, 48.0, 80.0, "GRADE_A", "SUPER", False, 0.03, 0.01, 0.01),
            (53.5, 51.5, 90.0, "GRADE_A", "SUPER", False, 0.02, 0.01, 0.01),
            (51.2, 49.0, 83.5, "GRADE_A", "SUPER", False, 0.05, 0.02, 0.01),
            (55.0, 52.8, 95.0, "GRADE_A", "SUPER", False, 0.04, 0.01, 0.01),
            (47.5, 45.5, 72.0, "GRADE_A", "SUPER", False, 0.03, 0.01, 0.01),
            # URS (Minor skin damage / slight off-size)
            (42.5, 40.0, 55.0, "URS", "MADHYAM", False, 0.65, 0.03, 0.02),
            (43.8, 41.5, 58.5, "URS", "MADHYAM", False, 0.72, 0.02, 0.01),
            (66.5, 63.0, 135.0, "URS", "JUMBO", False, 0.55, 0.04, 0.02),
            # Rejected (Biological soft rot)
            (48.0, 46.0, 75.0, "REJECTED", "SUPER", False, 0.40, 0.88, 0.05),
        ]

        for idx, (eq_d, pol_l, mass, grade, size_tier, uncert, p_dmg, p_rot, p_spr) in enumerate(calipers):
            inst = OnionInstance(
                id=f"inst-{sample.id[:8]}-{idx:02d}",
                sample_id=sample.id,
                instance_index=idx,
                bbox_x=50 + (idx % 5) * 180,
                bbox_y=50 + (idx // 5) * 140,
                bbox_w=120,
                bbox_h=110,
                segmentation_conf=0.92,
                touches_border=False,
                crop_path=f"crops/{inspection.id}/{sample.id}/{idx:04d}.jpg",
                mask_path=f"masks/{inspection.id}/{sample.id}/{idx:04d}.png",
            )
            db.add(inst)
            db.flush()

            meas = Measurement(
                id=f"meas-{inst.id}",
                onion_instance_id=inst.id,
                equivalent_diameter_mm=eq_d,
                equatorial_diameter_mm=eq_d,
                polar_length_mm=pol_l,
                estimated_weight_grams=mass,
                mandi_size_grade=size_tier,
                mask_area_px=int(3.14159 * ((eq_d / (2 * 0.6836)) ** 2)),
                scale_mm_per_px=0.6836,
                uncertainty_flag=uncert,
            )
            db.add(meas)

            defect = DefectObservation(
                id=f"def-{inst.id}",
                onion_instance_id=inst.id,
                damaged_prob=p_dmg,
                rotten_prob=p_rot,
                sprouted_prob=p_spr,
                model_version="mock-defect-classifier:v1",
                is_mock=True,
                final_decision=json.dumps({"damaged_prob": p_dmg, "rotten_prob": p_rot, "sprouted_prob": p_spr}),
            )
            db.add(defect)

            clf = ClassificationResult(
                id=f"clf-{inst.id}",
                onion_instance_id=inst.id,
                grade=grade,
                rejection_reasons="[]" if grade == "GRADE_A" else json.dumps([grade]),
                confidence_tier="HIGH" if grade == "GRADE_A" else "NEEDS_REVIEW",
                ruleset_version="DEMO_ASSUMPTION_v1",
                explanation=f"{'Grade A Prime' if grade == 'GRADE_A' else grade}",
            )
            db.add(clf)

        # Seed Report
        report = Report(
            id=DEMO_REPORT_ID,
            report_id=DEMO_REPORT_ID,
            inspection_id=inspection.id,
            total_bulbs=20,
            grade_a_count=16,
            urs_count=3,
            rejected_count=1,
            defect_counts=json.dumps({"damaged": 3, "rotten": 1, "sprouted": 0}),
            ruleset_version="DEMO_ASSUMPTION_v1",
            model_version="yolo11n-seg:mandi-onion-v1",
            share_token=DEMO_SHARE_TOKEN,
            pdf_path=f"reports/{DEMO_REPORT_ID}.pdf",
            sampling_note="Seeded demo lot: 1 sample photo (20 bulbs). Does not represent a real consignment.",
            created_at=now,
        )
        db.add(report)
        db.commit()

        # Generate the demo PDF report
        try:
            generate_pdf_report(report, inspection, output_dir=settings.storage_dir / "reports")
            logger.info("Demo PDF report successfully generated at storage/reports/%s.pdf", DEMO_REPORT_ID)
        except Exception as e:
            logger.warning("Could not pre-render demo PDF report: %s", e)

        logger.info("Demo inspection seed completed successfully: inspection_id=%s, share_token=%s", inspection.id, DEMO_SHARE_TOKEN)

    except Exception as exc:
        db.rollback()
        logger.exception("Failed during seed_demo_data_if_empty: %s", exc)
    finally:
        db.close()
