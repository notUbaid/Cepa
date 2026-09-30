import os
import logging
from pathlib import Path
from roboflow import Roboflow
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ml_train_detector")

def train_onion_detector():
    """
    Trains the YOLOv11 Onion Detector using the Roboflow dataset.
    """
    logger.info("Initializing Roboflow...")
    
    # Try to get API key from environment
    api_key = os.environ.get("ROBOFLOW_API_KEY")
    if not api_key:
        logger.error("ROBOFLOW_API_KEY not found in environment. Cannot download dataset.")
        logger.info("To proceed, provide your Roboflow API key.")
        return
        
    try:
        rf = Roboflow(api_key=api_key)
        project = rf.workspace("kush-maurya").project("onions-r8sei-kuogb")
        version = project.version(1)
        logger.info("Downloading YOLOv11 format dataset...")
        dataset = version.download("yolov11")
        
        logger.info(f"Dataset downloaded to {dataset.location}")
        
        # Train YOLO detector
        logger.info("Initializing YOLOv11 Nano...")
        model = YOLO("yolo11n.pt")  # Use Nano for speed
        
        logger.info("Starting training...")
        model.train(
            data=f"{dataset.location}/data.yaml",
            epochs=5,  # Short epoch for demonstration
            imgsz=640,
            project="ml/models",
            name="onion_detector"
        )
        
        logger.info("Training complete. Model saved to ml/models/onion_detector/weights/best.pt")
        
    except Exception as e:
        logger.error(f"Failed to train detector: {e}")

if __name__ == "__main__":
    train_onion_detector()
