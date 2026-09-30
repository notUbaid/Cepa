"""
Shared pytest fixtures for Cepa backend test suite.
"""
from __future__ import annotations

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from grading.policy_loader import GradingPolicy, load_policy
from grading.engine import GradingEngine


@pytest.fixture(scope="session")
def client():
    """Session-scoped TestClient that triggers FastAPI lifespan events."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def demo_policy() -> GradingPolicy:
    policies_dir = Path(__file__).parent.parent / "grading" / "policies"
    return load_policy("DEMO_ASSUMPTION_v1", policies_dir)


@pytest.fixture
def grading_engine(demo_policy: GradingPolicy) -> GradingEngine:
    return GradingEngine(demo_policy)
