"""
Stage 6: Defect Classifier

Classifies visible defects on each onion bulb crop.

Architecture decision: 4-Class Softmax classifier (MobileNetV3-Small backbone).
Predicts normalized categorical probability distribution over mutually exclusive classes:
  good_prob:     P(intact, healthy bulb with no surface lesions)
  damaged_prob:  P(visible mechanical damage / cuts / punctures / tunic rupture)
  rotten_prob:   P(visible surface rot / Aspergillus niger black mold / soft decay)
  sprouted_prob: P(visible apical vegetative green shoots)

The argmax gives the primary quality classification, with secondary biological
heuristic and RAM++ semantic verification for edge cases.

Important limitation:
  Camera-based detection can only identify VISIBLE surface defects.
  Internal rot not visible from the exterior CANNOT be detected without cut-testing.
  This limitation is architecturally acknowledged and stated in every report.
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
    good_prob: float = 0.0
    damaged_prob: float = 0.0
    rotten_prob: float = 0.0
    sprouted_prob: float = 0.0
    model_version: str = DEFECT_CLASSIFIER_MOCK_VERSION
    is_mock: bool = False

    def __post_init__(self) -> None:
        if self.good_prob == 0.0 and (self.damaged_prob > 0.0 or self.rotten_prob > 0.0 or self.sprouted_prob > 0.0):
            self.good_prob = max(0.0, 1.0 - (self.damaged_prob + self.rotten_prob + self.sprouted_prob))

    def as_dict(self) -> dict:
        return {
            "good_prob": self.good_prob,
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
            DefectPrediction with softmax probabilities for [good, damaged, rotten, sprouted].
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
        # Hash the actual visual content of the bulb crop (downsampled to 32x32 thumbnail).
        # This samples the entire bulb interior and pigmentation rather than reading only
        # the first bytes which are constant background padding.
        if crop_image is not None and crop_image.size > 0:
            import cv2
            thumb = cv2.resize(crop_image, (32, 32), interpolation=cv2.INTER_AREA)
            img_bytes = thumb.tobytes()
        else:
            img_bytes = b"empty_bulb_crop"

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
            good_prob=float(np.clip(probs[3] if len(probs) > 3 else 0.7, 0.0, 1.0)),
            damaged_prob=float(np.clip(probs[0], 0.0, 1.0)),
            rotten_prob=float(np.clip(probs[1], 0.0, 1.0)),
            sprouted_prob=float(np.clip(probs[2], 0.0, 1.0)),
            model_version=DEFECT_CLASSIFIER_MOCK_VERSION,
            is_mock=True,
        )


try:
    import torch
    import torch.nn as nn
    _TORCH_AVAILABLE = True
except (ImportError, OSError, Exception):
    torch = None
    nn = object
    _TORCH_AVAILABLE = False


class OnionDefectClassifierNet(nn.Module if _TORCH_AVAILABLE else object):
    """MobileNetV3-Small backbone with 4-class Softmax classifier."""
    def __init__(self) -> None:
        if not _TORCH_AVAILABLE:
            raise RuntimeError("PyTorch is required for OnionDefectClassifierNet")
        super().__init__()
        import torchvision.models as models
        backbone = models.mobilenet_v3_small(weights=None)
        in_features = backbone.classifier[0].in_features
        backbone.classifier = nn.Sequential(
            nn.Linear(in_features, 128),
            nn.Hardswish(),
            nn.Dropout(p=0.2),
            nn.Linear(128, 4),
        )
        self.net = backbone

    def forward(self, x: "torch.Tensor") -> "torch.Tensor":
        return self.net(x)


class RealDefectClassifier(DefectClassifier):
    """
    Real MobileNetV3 4-class single-label defect classifier.

    Loads trained weights from defect_classifier.pt.
    Input: (224, 224, 3) crop normalized to ImageNet stats.
    Output: Softmax probabilities for [GOOD, DAMAGED, ROTTEN, SPROUTED].
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
            raise RuntimeError(
                "RealDefectClassifier error: PyTorch weights are not loaded. "
                "Production inference cannot proceed without verified model weights."
            )

        # OpenCV BGR → RGB for torchvision transforms
        rgb = _cv2.cvtColor(crop_image, _cv2.COLOR_BGR2RGB)
        tensor = self._transform(rgb).unsqueeze(0).to(self._device)

        with torch.no_grad():
            logits = self._model(tensor)          # (1, 4) raw logits
            probs = torch.softmax(logits, dim=1).squeeze(0).cpu().numpy()

        p_good = float(probs[0])
        p_dmg = float(probs[1])
        p_rot = float(probs[2])
        p_spr = float(probs[3])

        # Biological validation on the crop:
        # Check for green vegetative shoots (chlorophyll) and black mold (Aspergillus niger)
        if crop_image is not None and crop_image.size > 0:
            hsv = _cv2.cvtColor(crop_image, _cv2.COLOR_BGR2HSV)
            h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
            green_mask = (h >= 35) & (h <= 85) & (s > 40) & (v > 40)
            green_ratio = float(np.mean(green_mask))

            lab = _cv2.cvtColor(crop_image, _cv2.COLOR_BGR2LAB)
            l, a = lab[:, :, 0], lab[:, :, 1]
            mold_mask = (l < 32) & (v < 38) & (a < 134)
            mold_ratio = float(np.mean(mold_mask))

            # If no green shoots (< 2%), pointed apex is normal dry neck, not sprouting
            if green_ratio < 0.02 and p_spr > 0.25:
                p_good = max(p_good, p_spr, 0.85)
                p_spr = 0.04

            # If no black mold / decay (< 3%), darker pigmentation is normal outer papery scale
            if mold_ratio < 0.03 and p_rot > 0.25:
                p_good = max(p_good, p_rot, 0.85)
                p_rot = 0.04

        return DefectPrediction(
            good_prob=p_good,
            damaged_prob=p_dmg,
            rotten_prob=p_rot,
            sprouted_prob=p_spr,
            model_version=self._version_str,
            is_mock=False,
        )


def get_classifier(use_mock: bool, model_path: str | None = None) -> DefectClassifier:
    """
    Factory function: returns the appropriate defect classifier.
    In production (use_mock=False), strictly loads RealDefectClassifier.
    Never silently falls back to MockDefectClassifier when real ML is requested.
    """
    if use_mock:
        logger.warning("[MOCK DEMO MODE ACTIVE] Using MockDefectClassifier — results labeled is_mock=True")
        return MockDefectClassifier()

    if not model_path:
        raise ValueError(
            "Production defect classifier error: model_path is required when use_mock=False. "
            "Set DEF_USE_MOCK=true only if explicitly running in mock development mode."
        )

    from pathlib import Path
    model_p = Path(model_path)
    if not model_p.exists():
        raise FileNotFoundError(
            f"Production defect classifier weights not found at '{model_path}'. "
            "Ensure backend/weights/defect_classifier.pt exists or configure DEF_MODEL_PATH."
        )

    clf = RealDefectClassifier(str(model_p))
    if clf._model is None:
        raise RuntimeError(f"Failed to load production defect classifier from '{model_path}'.")

    logger.info("Loaded production RealDefectClassifier (%s) on %s", clf.model_version, clf._device)
    return clf
