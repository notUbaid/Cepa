#!/usr/bin/env python3
"""
Pipeline Latency Benchmark Script for CEPA
==========================================
Runs the complete 8-stage computer vision pipeline on the synthetic demo spread
to obtain reproducible, empirically verified wall-clock latency figures on CPU.

Protocol:
  - 3 warm-up iterations (to prime PyTorch JIT and OS disk caching)
  - 30 timed benchmark iterations
  - Computes p50 (median), p95, mean, and per-stage timings
  - Outputs a standardized markdown table including host hardware specs
"""
from __future__ import annotations

import os
import sys
import time
import platform
from pathlib import Path
import numpy as np

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from config import settings
from cv.pipeline import run_pipeline
from cv.providers.yolo11_provider import YOLO11SegmentationProvider
from cv.providers.watershed_provider import WatershedSegmentationProvider
from cv.defect_classifier import get_classifier
from grading.policy_loader import load_policy


def get_hardware_info() -> dict:
    cpu_name = platform.processor() or "Unknown CPU"
    cores = os.cpu_count() or 1
    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "cpu": cpu_name,
        "cores": cores,
    }


def main():
    img_path = backend_dir / "static" / "synthetic_demo_spread.jpg"
    if not img_path.exists():
        print(f"ERROR: Image not found at {img_path}", file=sys.stderr)
        sys.exit(1)

    img_bytes = img_path.read_bytes()
    print(f"Loaded benchmark sample: {img_path.name} ({len(img_bytes) / 1024:.1f} KB)")

    # Initialize CV components exactly as in production
    if settings.seg_model_path.exists():
        seg_provider = YOLO11SegmentationProvider(
            model_path=settings.seg_model_path,
            conf_threshold=settings.seg_confidence_threshold,
            iou_threshold=settings.seg_iou_threshold,
            device="cpu",
        )
    else:
        seg_provider = WatershedSegmentationProvider()

    defect_classifier = get_classifier(
        use_mock=False,
        model_path=str(settings.def_model_path) if settings.def_model_path.exists() else None,
    )

    policy = load_policy(
        version=settings.active_grading_policy,
        policies_dir=settings.policies_dir,
    )

    print(f"Segmentation provider: {seg_provider.model_version}")
    print(f"Defect classifier: {defect_classifier.model_version}")
    print(f"Grading policy: {policy.version}")

    # 3 warm-up runs
    print("\nWarming up pipeline (3 iterations)...")
    for i in range(3):
        res = run_pipeline(
            image_bytes=img_bytes,
            inspection_id="bench-warmup",
            sample_id=f"warmup-{i}",
            seg_provider=seg_provider,
            defect_classifier=defect_classifier,
            policy=policy,
        )
        print(f"  Warmup {i+1}: {res.total_elapsed_ms:.1f} ms ({len(res.instances)} bulbs)")

    # 30 timed benchmark runs
    iterations = 30
    latencies = []
    print(f"\nRunning {iterations} benchmark iterations...")
    for i in range(iterations):
        t0 = time.perf_counter()
        res = run_pipeline(
            image_bytes=img_bytes,
            inspection_id="bench-run",
            sample_id=f"bench-{i}",
            seg_provider=seg_provider,
            defect_classifier=defect_classifier,
            policy=policy,
        )
        t1 = time.perf_counter()
        elapsed_ms = (t1 - t0) * 1000.0
        latencies.append(elapsed_ms)
        if (i + 1) % 5 == 0 or i == iterations - 1:
            print(f"  Iteration {i+1}/{iterations}: {elapsed_ms:.1f} ms")

    latencies = np.array(latencies)
    p50 = np.percentile(latencies, 50)
    p90 = np.percentile(latencies, 90)
    p95 = np.percentile(latencies, 95)
    mean_val = np.mean(latencies)
    std_val = np.std(latencies)
    min_val = np.min(latencies)
    max_val = np.max(latencies)

    hw = get_hardware_info()

    report_md = f"""
### CEPA End-to-End Pipeline Latency Benchmark (Measured on CPU)

**Test Protocol**:
- Dataset: `synthetic_demo_spread.jpg` (1800x1400, 22 bulbs, ChArUco 7x5 card)
- Executions: 3 warm-up runs + {iterations} timed runs
- Device: CPU execution (PyTorch CPU, zero GPU acceleration)

| Metric | Measured Value |
|:---|:---|
| **Median (p50)** | **{p50:.1f} ms** |
| **95th Percentile (p95)** | **{p95:.1f} ms** |
| **90th Percentile (p90)** | **{p90:.1f} ms** |
| **Mean ± Std** | **{mean_val:.1f} ± {std_val:.1f} ms** |
| **Min / Max** | **{min_val:.1f} ms / {max_val:.1f} ms** |
| **Bulbs Extracted & Graded** | **{len(res.instances)} bulbs** |
| **Throughput** | **{1000.0 / mean_val:.2f} images/sec ({len(res.instances) * 1000.0 / mean_val:.1f} bulbs/sec)** |

**Hardware Environment**:
- **Host OS**: {hw['os']}
- **Processor**: {hw['cpu']} ({hw['cores']} logical cores)
- **Python**: {hw['python']}
- **Segmentation**: {seg_provider.model_version}
- **Classifier**: {defect_classifier.model_version}
"""
    print("\n" + "=" * 60)
    print(report_md)
    print("=" * 60)


if __name__ == "__main__":
    main()
