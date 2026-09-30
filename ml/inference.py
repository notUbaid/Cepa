import logging
from pathlib import Path
import numpy as np

# Use the backend's RealDefectClassifier for PyTorch model inference
import sys
import os
backend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if backend_path not in sys.path:
    sys.path.append(backend_path)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # also add root
from cv.defect_classifier import RealDefectClassifier, DefectPrediction

from ml.ram_service import RAMService
from ml.quality_decision import QualityDecisionEngine
import yaml

logger = logging.getLogger(__name__)

class QualityInferencePipeline:
    def __init__(self, config_path="ml/config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
            
        model_path = self.config["model"]["weights_path"]
        self.quality_model = RealDefectClassifier(model_path)
        
        self.ram_service = None
        if self.config["ram_plus_plus"]["enabled"]:
            self.ram_service = RAMService(
                model_type=self.config["ram_plus_plus"]["model_type"],
                image_size=self.config["ram_plus_plus"]["image_size"]
            )
            self.ram_service.load_model()
            
        self.decision_engine = QualityDecisionEngine("ml/quality_mapping.yaml")
        
        self.model_version = f"onion-quality-v2:ram++:{self.quality_model.model_version}"
        self.is_mock = False

    def predict(self, crop_image: np.ndarray):
        """
        Runs the full quality inference pipeline on a cropped onion.
        1. Trained PyTorch Quality Model -> probabilities
        2. RAM++ -> Semantic tags
        3. Quality Logic Engine -> Final decision
        """
        # 1. Base probabilities from custom trained MobileNet
        base_prediction: DefectPrediction = self.quality_model.classify(crop_image)
        base_probs = base_prediction.as_dict()
        
        # 2. Extract semantic tags via RAM++
        ram_tags = []
        if self.ram_service and self.ram_service.model:
            ram_tags = self.ram_service.recognize_tags(crop_image)
            
        # 3. Decision Engine fuses both sources
        decision = self.decision_engine.analyze(base_probs, ram_tags)
        
        return decision
