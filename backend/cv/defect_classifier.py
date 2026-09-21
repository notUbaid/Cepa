"""
Stage 6: Defect Classifier

Classifies visible defects on each onion bulb crop.

Architecture decision: MULTI-LABEL sigmoid output (not softmax).
Each defect is an independent binary probability:
  damaged_prob:  P(visible mechanical damage / cuts / bruising)
  rotten_prob:   P(visible surface rot / decay / mold)
  sprouted_prob: P(visible sprouting / green shoots)

These probabilities are independent — a single bulb can simultaneously
have damaged=0.9, rotten=0.1, sprouted=0.8 (old sprouted damaged bulb).

Important limitation:
  Camera-based detection can only identify VISIBLE surface defects.
  Internal rot not visible from the exterior CANNOT be detected.
  This limitation is architecturally acknowledged and stated in every report.

Phase 1 uses MockDefectClassifier (deterministic, image-hash-seeded).
Replace with RealDefectClassifier once training data is collected.
"""
from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

DEFECT_CLASSIFIER_MOCK_VERSION = "mock-defect-classifier:v1"


@dataclass
class DefectPrediction:
    """Per-onion defect classification output."""
    damaged_prob: float
    rotten_prob: float
    sprouted_prob: float
    model_version: str
    is_mock: bool

    def as_dict(self) -> dict:
        return {
            "damaged_prob": self.damaged_prob,
            "rotten_prob": self.rotten_prob,
            "sprouted_prob": self.sprouted_prob,
        }


class DefectClassifier(ABC):
    """Abstract base for defect classifiers."""

    @property
    @abstractmethod
    def model_version(self) -> str: ...

    @property
    @abstractmethod
    def is_mock(self) -> bool: ...

    @abstractmethod
    def classify(self, crop_image: np.ndarray) -> DefectPrediction:
        """
        Classify defects on a single onion crop.

        Args:
            crop_image: BGR uint8 numpy array of the masked onion crop.
                        Typically ~(150-300, 150-300, 3).

        Returns:
            DefectPrediction with sigmoid probabilities for each defect.
        """
        ...

    def classify_batch(self, crops: list[np.ndarray]) -> list[DefectPrediction]:
        """Default: classify one by one. Override for batched inference."""
        return [self.classify(c) for c in crops]


class MockDefectClassifier(DefectClassifier):
    """
    DETERMINISTIC mock defect classifier for Phase 1 and testing.

    Generates realistic-looking but seeded-random probabilities.
    The seed is derived from the crop image content hash, so:
      - Same image always → same prediction (reproducible demo)
      - Different images → different predictions (appears realistic)

    Output distribution is skewed toward low probabilities (most onions
    appear healthy) with occasional high-probability defect simulations.

    IMPORTANT: All outputs are marked is_mock=True. The API and UI
    must display a prominent [MOCK PREDICTIONS] warning when this
    classifier is active.
    """

    @property
    def model_version(self) -> str:
        return DEFECT_CLASSIFIER_MOCK_VERSION

    @property
    def is_mock(self) -> bool:
        return True

    def classify(self, crop_image: np.ndarray) -> DefectPrediction:
        # Hash the crop content for deterministic seeding
        # Use first 2000 bytes to limit hashing time on large crops
        img_bytes = crop_image.tobytes()[:2000]
        h = hashlib.md5(img_bytes).hexdigest()
        seed = int(h[:8], 16) % (2**31)
        rng = np.random.RandomState(seed)

        # Beta distribution: alpha=2, beta=8 → skewed toward 0
        # (most onions are healthy in a normal lot)
        # Occasionally simulate a defective onion with higher probs
        defect_seed = int(h[8:10], 16) % 100
        if defect_seed < 15:
            # ~15% chance of a clearly defective onion
            # Pick one dominant defect
            which = rng.randint(0, 3)
            probs = rng.beta([2, 2, 2], [8, 8, 8])  # base healthy probs
            probs[which] = rng.uniform(0.65, 0.95)   # dominant defect
        elif defect_seed < 30:
            # ~15% chance of borderline defect (challenging for reviewer)
            probs = rng.beta([4, 4, 4], [6, 6, 6])
        else:
            # ~70% chance of healthy onion
            probs = rng.beta([2, 2, 2], [8, 8, 8])

        return DefectPrediction(
            damaged_prob=float(np.clip(probs[0], 0.0, 1.0)),
            rotten_prob=float(np.clip(probs[1], 0.0, 1.0)),
            sprouted_prob=float(np.clip(probs[2], 0.0, 1.0)),
            model_version=DEFECT_CLASSIFIER_MOCK_VERSION,
            is_mock=True,
        )


import torch.nn as nn


class OnionDefectClassifierNet(nn.Module):
    """MobileNetV3-Small backbone with multi-label sigmoid classifier."""
    def __init__(self) -> None:
        super().__init__()
        import torchvision.models as models
        backbone = models.mobilenet_v3_small(weights=None)
        in_features = backbone.classifier[0].in_features
        backbone.classifier = nn.Sequential(
            nn.Linear(in_features, 128),
            nn.Hardswish(),
            nn.Dropout(p=0.2),
            nn.Linear(128, 3),
        )
        self.net = backbone

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class RealDefectClassifier(DefectClassifier):
    """
    Real MobileNetV3 multi-label defect classifier.

    Loads trained weights from defect_classifier.pt.
    Input: (224, 224, 3) crop normalized to ImageNet stats.
    Output: sigmoid probabilities for [damaged, rotten, sprouted].
    """

    def __init__(self, model_path: str) -> None:
        from pathlib import Path
        import torch
        import torchvision.transforms as T

        self._path = Path(model_path)
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._transform = T.Compose([
            T.ToPILImage(),
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        self._model = None
        self._version_str = f"defect-classifier:{self._path.stem}"
        self._load()

    def _load(self) -> None:
        import torch
        if not self._path.exists():
            logger.warning(
                "Defect classifier weights not found at %s. Using mock.", self._path
            )
            return
        try:
            model = OnionDefectClassifierNet()
            state = torch.load(str(self._path), map_location=self._device, weights_only=True)
            if hasattr(state, "state_dict"):
                state = state.state_dict()
            model.load_state_dict(state)
            model.eval()
            self._model = model.to(self._device)
            logger.info("Real defect classifier loaded from %s on %s", self._path, self._device)
        except Exception:
            logger.exception("Failed to load defect classifier from %s", self._path)

    @property
    def model_version(self) -> str:
        return self._version_str

    @property
    def is_mock(self) -> bool:
        return False

    def classify(self, crop_image: np.ndarray) -> DefectPrediction:
        import cv2 as _cv2
        import torch

        if self._model is None:
            logger.warning("Real defect classifier not loaded — falling back to mock")
            return MockDefectClassifier().classify(crop_image)

        # OpenCV BGR → RGB for torchvision transforms
        rgb = _cv2.cvtColor(crop_image, _cv2.COLOR_BGR2RGB)
        tensor = self._transform(rgb).unsqueeze(0).to(self._device)

        with torch.no_grad():
            logits = self._model(tensor)          # (1, 3) raw logits
            probs = torch.sigmoid(logits).squeeze(0).cpu().numpy()

        return DefectPrediction(
            damaged_prob=float(probs[0]),
            rotten_prob=float(probs[1]),
            sprouted_prob=float(probs[2]),
            model_version=self._version_str,
            is_mock=False,
        )


def get_classifier(use_mock: bool, model_path: str | None = None) -> DefectClassifier:
    """
    Factory function: returns the appropriate defect classifier.

    Args:
        use_mock: If True, always use MockDefectClassifier.
        model_path: Path to real model weights (required if use_mock=False).
    """
    if use_mock:
        logger.info("Using MockDefectClassifier — results will be labelled [MOCK]")
        return MockDefectClassifier()
    if model_path:
        try:
            clf = RealDefectClassifier(model_path)
            if clf._model is not None:
                return clf
        except Exception:
            logger.exception("RealDefectClassifier failed to load, falling back to mock")
    logger.warning("Falling back to MockDefectClassifier — no valid model path provided")
    return MockDefectClassifier()
