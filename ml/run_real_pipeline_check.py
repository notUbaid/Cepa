import time
import cv2
import logging
import json
from pathlib import Path

# Try importing ultralytics. If missing, we mock it since we are asked to use it but we might lack Roboflow dataset
try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False

from ml.inference import QualityInferencePipeline

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("test_real")

def test_image(pipeline, image_path: str):
    logger.info("=" * 60)
    logger.info(f"INPUT: {image_path}")
    
    t_start = time.time()
    
    img = cv2.imread(image_path)
    if img is None:
        logger.error("Failed to read image.")
        return
        
    # 1. Detector Mock / YOLO
    t_det_start = time.time()
    bbox = [0, 0, img.shape[1], img.shape[0]]
    conf = 1.0
    
    detector_model_path = Path("ml/models/onion_detector/weights/best.pt")
    if HAS_YOLO and detector_model_path.exists():
        detector = YOLO(str(detector_model_path))
        results = detector.predict(img, verbose=False)
        if len(results[0].boxes) > 0:
            best_box = results[0].boxes[0]
            conf = float(best_box.conf)
            x1, y1, x2, y2 = map(int, best_box.xyxy[0])
            bbox = [x1, y1, x2, y2]
            img = img[y1:y2, x1:x2]
    
    detector_time = (time.time() - t_det_start) * 1000
    
    logger.info(f"DETECTOR RESULT:       BBox {bbox}")
    logger.info(f"DETECTOR CONFIDENCE:   {conf:.2%}")
    
    # 2. Quality Pipeline (Model + RAM + Decision)
    t_qual_start = time.time()
    
    # We monkey-patch the timing in RAMService if needed, but we can just measure overall here
    try:
        result = pipeline.predict(img)
    except Exception as e:
        logger.error(f"Inference failed: {e}")
        return
        
    quality_time = (time.time() - t_qual_start) * 1000
    total_time = (time.time() - t_start) * 1000
    
    logger.info(f"QUALITY PROBABILITIES: {json.dumps(result['probabilities'])}")
    logger.info(f"QUALITY CLASS:         {result['quality_class']}")
    logger.info(f"QUALITY CONFIDENCE:    {result['quality_confidence']:.2f}")
    logger.info(f"RAM TAGS:              {result['semantic_tags']}")
    
    # Extract final decision from quality class
    final_decision = result['quality_class']
    if final_decision in ["DAMAGED", "ROTTEN", "SPROUTED"]:
        final_decision = "BAD"
        
    logger.info(f"FINAL DECISION:        {final_decision}")
    logger.info(f"TOTAL INFERENCE TIME:  {total_time:.2f} ms")
    logger.info(f"  - Detector Time:     {detector_time:.2f} ms")
    logger.info(f"  - Quality/RAM Time:  {quality_time:.2f} ms")
    
def run_tests():
    pipeline = QualityInferencePipeline("ml/config.yaml")
    
    test_images = [
        "cv_tools/dataset/real_onions/crops/healthy/real_healthy_File_Three_whole_red_onions_05.jpg",
        "cv_tools/dataset/real_onions/crops/damaged/real_damaged_File_Onion_Peel_00.jpg",
        "cv_tools/dataset/real_onions/crops/rotten/real_rotten_File_Insect_pests_of_farm__garden_and_orchard__1912___14591969157__17.jpg",
        "cv_tools/dataset/real_onions/crops/sprouted/real_sprouted_File_White_onion_bulb_sprouting1_27.jpg"
    ]
    
    for path in test_images:
        test_image(pipeline, path)
        
    logger.info("=" * 60)

if __name__ == "__main__":
    run_tests()
