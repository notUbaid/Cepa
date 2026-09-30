import os
import sys
import time
import cv2
import logging
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.inference import QualityInferencePipeline
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ml_full_pipeline")

def test_full_pipeline(image_path: str):
    logger.info(f"Starting End-to-End Pipeline on image: {image_path}")
    start_time = time.time()
    
    # 1. Detector Step
    detector_start = time.time()
    detector_path = Path("ml/models/onion_detector/weights/best.pt")
    if not detector_path.exists():
        logger.warning(f"Custom Roboflow detector not found at {detector_path}.")
        logger.warning("Using base YOLOv11 for demonstration. (Run train_detector.py with ROBOFLOW_API_KEY to train custom model)")
        detector_model = YOLO("yolo11n.pt")
    else:
        logger.info("Loading custom Roboflow Onion Detector...")
        detector_model = YOLO(detector_path)
    
    img = cv2.imread(image_path)
    if img is None:
        logger.error("Failed to read image.")
        return
        
    results = detector_model.predict(img, verbose=False)
    boxes = results[0].boxes
    
    if len(boxes) == 0:
        logger.warning("No onions detected in the image using base COCO model.")
        logger.warning("Bypassing cropping and feeding raw image to Quality Pipeline...")
        crop = img
        x1, y1, x2, y2 = 0, 0, img.shape[1], img.shape[0]
        conf = 1.0
    else:
        # Get highest confidence detection
        best_box = boxes[0]
        conf = float(best_box.conf)
        x1, y1, x2, y2 = map(int, best_box.xyxy[0])
        cls_id = int(best_box.cls)
        
        logger.info(f"Detection: class={cls_id}, conf={conf:.4f}, bbox=[{x1}, {y1}, {x2}, {y2}]")
        logger.info(f"Detector Inference Time: {(time.time() - detector_start) * 1000:.2f} ms")
        
        # 2. Crop
        crop = img[y1:y2, x1:x2]
    
    # 3. Quality Inference (MobileNetV3 + RAM++ + Decision)
    logger.info("Initializing Quality Pipeline...")
    pipeline = QualityInferencePipeline("ml/config.yaml")
    
    quality_start = time.time()
    result = pipeline.predict(crop)
    quality_time = (time.time() - quality_start) * 1000
    
    total_time = (time.time() - start_time) * 1000
    
    print("\n" + "="*50)
    print("      END-TO-END INFERENCE RESULTS")
    print("="*50)
    print(f"File:            {image_path}")
    print(f"Total Time:      {total_time:.2f} ms")
    print(f"Detector Time:   {(time.time() - detector_start)*1000 - quality_time:.2f} ms")
    print(f"Quality Time:    {quality_time:.2f} ms")
    print("-" * 50)
    print("1. DETECTOR (Roboflow YOLO)")
    print(f"   BBox:         [{x1}, {y1}, {x2}, {y2}]")
    print(f"   Confidence:   {conf:.2%}")
    print("-" * 50)
    print("3. SEMANTIC RECOGNITION (RAM++)")
    print(f"   Tags:         {result['ram_tags']}")
    print("-" * 50)
    print("4. DECISION ENGINE")
    print(f"   Adj Probs:    {result['adjusted_probs']}")
    print(f"   Reasons:      {result['reasons']}")
    print(f"   Score:        {result['score']:.2f}")
    print(f"   FINAL RESULT: {result['result']}")
    print("="*50)


if __name__ == "__main__":
    # Test on a source image from the real dataset
    test_img = "cv_tools/dataset/real_onions/healthy/real_healthy_healthy_onion.jpg"
    if len(sys.argv) > 1:
        test_img = sys.argv[1]
    
    if os.path.exists(test_img):
        test_full_pipeline(test_img)
    else:
        logger.error(f"Test image {test_img} not found.")
