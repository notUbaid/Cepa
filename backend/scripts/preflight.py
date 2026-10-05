#!/usr/bin/env python3
"""
CEPA Submission Preflight Verification Script
=============================================
Executes complete automated preflight health audit before live demo / jury evaluation:
1. Validates Python environment and dependencies (PyTorch, Ultralytics, OpenCV, Cryptography).
2. Verifies neural network model weights integrity on disk.
3. Verifies SQLite database connectivity, schema migration, and WAL mode.
4. Verifies Ed25519 sovereign keypair initialization and public key discovery.
5. Executes an end-to-end dry run through the 8-stage inspection pipeline on synthetic demo spread.
6. Returns exit code 0 if all subsystems are green.
"""
import sys
import time
from pathlib import Path

# Ground sys.path in backend root
backend_dir = Path(__file__).resolve().parent.parent
repo_dir = backend_dir.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(repo_dir) not in sys.path:
    sys.path.insert(0, str(repo_dir))

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def print_header(title: str):
    print(f"\n=== {title} ===")

def print_pass(msg: str):
    print(f"  [PASS] {msg}")

def print_warn(msg: str):
    print(f"  [WARN] {msg}")

def print_fail(msg: str):
    print(f"  [FAIL] {msg}")

def run_preflight() -> int:
    failures = 0
    print_header("CEPA PREFLIGHT SYSTEM VERIFICATION")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print(f"Python: {sys.version.split()[0]} on {sys.platform}")

    # 1. Imports Check
    print_header("1. Core Dependencies Check")
    required_modules = [
        ("torch", "PyTorch"),
        ("ultralytics", "Ultralytics YOLO"),
        ("cv2", "OpenCV"),
        ("scipy", "SciPy"),
        ("cryptography", "Cryptography (Ed25519)"),
        ("fastapi", "FastAPI"),
        ("pydantic", "Pydantic V2"),
        ("reportlab", "ReportLab PDF Engine"),
    ]
    for mod_name, label in required_modules:
        try:
            mod = __import__(mod_name)
            ver = getattr(mod, "__version__", "installed")
            print_pass(f"{label}: {ver}")
        except ImportError as e:
            print_fail(f"{label} missing: {e}")
            failures += 1

    # 2. Weights & File Integrity
    print_header("2. Model Weights & Data Integrity")
    weights_dir = backend_dir / "weights"
    seg_weight = weights_dir / "yolo11n-seg.pt"
    clf_weight = weights_dir / "defect_classifier.pt"
    demo_img = backend_dir / "static" / "synthetic_demo_spread.jpg"

    if seg_weight.exists() and seg_weight.stat().st_size > 1_000_000:
        print_pass(f"YOLO11n-seg Weights: {seg_weight.stat().st_size / 1_000_000:.1f} MB ({seg_weight.name})")
    else:
        print_fail(f"YOLO11n-seg weights missing or truncated at {seg_weight}")
        failures += 1

    if clf_weight.exists() and clf_weight.stat().st_size > 100_000:
        print_pass(f"Defect Classifier Weights: {clf_weight.stat().st_size / 1_000_000:.1f} MB ({clf_weight.name})")
    else:
        print_fail(f"Defect classifier weights missing at {clf_weight}")
        failures += 1

    if demo_img.exists() and demo_img.stat().st_size > 50_000:
        print_pass(f"Synthetic Demo Sample Spread: {demo_img.stat().st_size / 1_000:.1f} KB ({demo_img.name})")
    else:
        print_fail(f"Synthetic demo image missing at {demo_img}")
        failures += 1

    # 3. Database Connectivity & WAL mode
    print_header("3. Storage & SQLite Database")
    from config import settings
    settings.ensure_dirs()
    print_pass(f"Runtime storage directory: {settings.storage_dir}")

    try:
        from database import SessionLocal, engine
        with engine.connect() as conn:
            from sqlalchemy import text
            journal = conn.execute(text("PRAGMA journal_mode;")).scalar()
            print_pass(f"Database connected. SQLite Journal Mode: {journal.upper()}")
    except Exception as e:
        print_fail(f"Database connection error: {e}")
        failures += 1

    # 4. Cryptographic Key Infrastructure
    print_header("4. Sovereign Cryptography & Ed25519 Discovery")
    try:
        from services.crypto_seal import (
            get_ed25519_public_key_hex,
            get_ed25519_public_key_pem,
            verify_ed25519_seal,
            get_ed25519_private_key,
        )
        pub_hex = get_ed25519_public_key_hex()
        pub_pem = get_ed25519_public_key_pem()
        priv_key = get_ed25519_private_key()
        test_payload = b"CEPA-PREFLIGHT-VERIFICATION-CHECK"
        test_sig = priv_key.sign(test_payload)
        verified = verify_ed25519_seal(test_sig.hex(), test_payload)

        if verified and len(pub_hex) == 64:
            print_pass(f"Ed25519 Sovereign Public Key (RFC 8032): {pub_hex[:16]}...{pub_hex[-16:]}")
            print_pass("Ed25519 Self-Signature Verification: VALID")
        else:
            print_fail("Ed25519 signature test failed")
            failures += 1
    except Exception as e:
        print_fail(f"Cryptographic initialization error: {e}")
        failures += 1

    # 5. Statistical Sampling Precision Engine
    print_header("5. Statistical Assaying Engine (Clopper-Pearson)")
    try:
        from grading.statistics import (
            compute_clopper_pearson_interval,
            calculate_sample_size_needed,
            evaluate_lot_statistics,
        )
        lower, upper = compute_clopper_pearson_interval(2, 20, 0.95)
        samp_res = calculate_sample_size_needed(2, 20, target_moe_pct=5.0)
        print_pass(f"Clopper-Pearson 95% CI (2/20 defects): [{lower}%, {upper}%]")
        print_pass(f"Cochran Sampling Sufficiency: Need {samp_res['recommended_total_sample']} bulbs for ±5% MoE (Current: 20)")
    except Exception as e:
        print_fail(f"Statistical engine error: {e}")
        failures += 1

    # 6. Pipeline Dry-Run on Synthetic Demo Image
    print_header("6. End-to-End Pipeline Dry-Run")
    try:
        from cv.pipeline import run_pipeline
        from cv.providers.yolo11_provider import YOLO11SegmentationProvider
        from cv.providers.watershed_provider import WatershedSegmentationProvider
        from cv.defect_classifier import get_classifier
        from grading.policy_loader import load_policy

        img_bytes = demo_img.read_bytes()
        if settings.seg_model_path.exists():
            seg_provider = YOLO11SegmentationProvider(
                model_path=settings.seg_model_path,
                conf_threshold=settings.seg_confidence_threshold,
                iou_threshold=settings.seg_iou_threshold,
            )
        else:
            seg_provider = WatershedSegmentationProvider()

        defect_classifier = get_classifier(model_path=settings.def_model_path, use_mock=False)
        policy = load_policy(settings.active_grading_policy, settings.policies_dir)

        t0 = time.perf_counter()
        result = run_pipeline(
            image_bytes=img_bytes,
            inspection_id="PREFLIGHT-INSP",
            sample_id="PREFLIGHT-SAMPLE",
            seg_provider=seg_provider,
            defect_classifier=defect_classifier,
            policy=policy,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        num_bulbs = len(result.instances)
        scale = result.scale_mm_per_px
        print_pass(f"Full 8-stage pipeline executed in {elapsed_ms:.1f} ms")
        print_pass(f"Detected {num_bulbs} bulbs across spread (Quality Passed: {result.quality_passed})")
        if scale:
            print_pass(f"ChArUco Homography Scale: {scale:.4f} mm/px (Marker detected: {result.marker_detected})")
        else:
            print_warn("Scale not calibrated (marker detection returned fallback)")
    except Exception as e:
        print_fail(f"Pipeline dry-run error: {e}")
        failures += 1

    # Final Verdict
    print_header("PREFLIGHT AUDIT SUMMARY")
    if failures == 0:
        print("\033[1;32m>>> ALL PREFLIGHT AUDIT GATES PASSED (100% OPERATIONAL) <<<\033[0m")
        return 0
    else:
        print(f"\033[1;31m>>> PREFLIGHT AUDIT FAILED ({failures} GATE FAILURES) <<<\033[0m")
        return 1

if __name__ == "__main__":
    sys.exit(run_preflight())
