import sys
import os
import cv2
from pathlib import Path
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.inference import QualityInferencePipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def run_test():
    # 1. Initialize Pipeline
    print("Initializing Quality Inference Pipeline...")
    pipeline = QualityInferencePipeline("ml/config.yaml")
    
    # 2. Find a test crop
    test_crops = list(Path("cv_tools/dataset/real_onions/crops/rotten").glob("*.jpg"))
    if not test_crops:
        test_crops = list(Path("cv_tools/dataset/real_onions/crops/healthy").glob("*.jpg"))
        
    if not test_crops:
        print("No test crops found. Run dataset fetcher first.")
        return
        
    test_img = str(test_crops[0])
    print(f"Running inference on {test_img}")
    
    crop = cv2.imread(test_img)
    
    # 3. Predict
    result = pipeline.predict(crop)
    
    print("\n--- INFERENCE RESULT ---")
    print(f"Final Decision: {result['result']}")
    print(f"Quality Score:  {result['score']}")
    print(f"Rejection Reasons: {result['reasons']}")
    print(f"RAM++ Tags: {result['ram_tags']}")
    print(f"Adjusted Probs: {result['adjusted_probs']}")
    
if __name__ == "__main__":
    run_test()
