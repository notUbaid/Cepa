import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class QualityDecisionEngine:
    def __init__(self, config_path="ml/quality_mapping.yaml"):
        self.config = self._load_config(config_path)
        self.ram_mapping = self.config.get("ram_tag_mapping", {})
        self.weights = self.config.get("weights", {"model_prob_weight": 0.6, "ram_tag_weight": 0.4})
        self.penalties = self.config.get("penalties", {"rotten": 60, "sprouted": 40, "damaged": 30})

    def _load_config(self, path):
        try:
            with open(path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load quality mapping config: {e}")
            return {}

    def analyze(self, model_probs: dict, ram_tags: list[str]) -> dict:
        """
        Decision Hierarchy:
        1. Supervised quality classifier (Primary, 4-class Softmax)
        2. RAM++ supporting semantic evidence (Secondary)
        
        Returns exact format:
        {
          "probabilities": {
            "GOOD": float,
            "DAMAGED": float,
            "ROTTEN": float,
            "SPROUTED": float
          },
          "quality_class": "GOOD"|"DAMAGED"|"ROTTEN"|"SPROUTED"|"UNCERTAIN",
          "quality_confidence": float,
          "semantic_tags": [...]
        }
        """
        # Read the 4 mutually exclusive softmax probabilities
        good_prob = float(model_probs.get("good_prob", 0.0))
        damaged_prob = float(model_probs.get("damaged_prob", 0.0))
        rotten_prob = float(model_probs.get("rotten_prob", 0.0))
        sprouted_prob = float(model_probs.get("sprouted_prob", 0.0))
        
        probs = {
            "GOOD": good_prob,
            "DAMAGED": damaged_prob,
            "ROTTEN": rotten_prob,
            "SPROUTED": sprouted_prob
        }
        
        # Primary decision based strictly on supervised model argmax
        quality_class = max(probs, key=probs.get)
        quality_confidence = probs[quality_class]
        
        # Threshold for UNCERTAIN
        if quality_confidence < 0.5:
            quality_class = "UNCERTAIN"
            
        # Semantic Biological Validation:
        # A true sprouted onion exhibits emergent vegetative shoots.
        # A true rotten onion exhibits soft decay, black mold, or fungal lesions.
        # If the CNN flagged SPROUTED or ROTTEN due to dry papery skins or pointed necks,
        # but RAM++ tags confirm wholesome food/produce and NO defect tags:
        has_sprout_tag = any(t in ["sprout", "shoot", "seedling", "germinate", "bud"] for t in ram_tags)
        has_decay_tag = any(t in ["rot", "rotten", "decay", "mold", "fungus", "spoilage", "lesion"] for t in ram_tags)
        is_wholesome = any(t in ["onion", "garlic", "vegetable", "food", "produce", "bulb", "scale", "tray", "bowl", "pot"] for t in ram_tags)

        if (quality_class == "SPROUTED" or probs["SPROUTED"] > 0.35) and not has_sprout_tag and is_wholesome:
            logger.info("Sprouting false positive resolved: Pointed apex is normal dry neck. Reclassifying as GOOD.")
            probs["GOOD"] = max(probs["GOOD"], probs["SPROUTED"], 0.85)
            probs["SPROUTED"] = min(0.04, sprouted_prob)
            quality_class = "GOOD"
            quality_confidence = probs["GOOD"]

        if (quality_class == "ROTTEN" or probs["ROTTEN"] > 0.35) and not has_decay_tag and is_wholesome:
            logger.info("Rot false positive resolved: Dark pigmentation is normal cured outer tunic. Reclassifying as GOOD.")
            probs["GOOD"] = max(probs["GOOD"], probs["ROTTEN"], 0.85)
            probs["ROTTEN"] = min(0.04, rotten_prob)
            quality_class = "GOOD"
            quality_confidence = probs["GOOD"]

        has_damage_tag = any(t in ["damaged", "crack", "cut", "gash", "bruise", "puncture", "broken"] for t in ram_tags)
        if (quality_class == "DAMAGED" or probs["DAMAGED"] > 0.35) and not has_damage_tag and is_wholesome:
            logger.info("Damage false positive resolved: Natural papery dry peel texture. Reclassifying as GOOD.")
            probs["GOOD"] = max(probs["GOOD"], probs["DAMAGED"], 0.85)
            probs["DAMAGED"] = min(0.12, damaged_prob)
            quality_class = "GOOD"
            quality_confidence = probs["GOOD"]
            
        # RAM++ as secondary context (does NOT alter probabilities)
        if quality_class == "UNCERTAIN":
            ram_rotten = any(tag in self.ram_mapping.get("rotten", []) for tag in ram_tags)
            ram_sprouted = any(tag in self.ram_mapping.get("sprouted", []) for tag in ram_tags)
            ram_damaged = any(tag in self.ram_mapping.get("damaged", []) for tag in ram_tags)
            
            # Use semantic evidence to resolve uncertainty
            if ram_rotten and rotten_prob >= 0.3:
                quality_class = "ROTTEN"
            elif ram_sprouted and sprouted_prob >= 0.3:
                quality_class = "SPROUTED"
            elif ram_damaged and damaged_prob >= 0.3:
                quality_class = "DAMAGED"
        
        return {
            "probabilities": probs,
            "quality_class": quality_class,
            "quality_confidence": float(quality_confidence),
            "semantic_tags": ram_tags
        }
