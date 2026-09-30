"""
ml/download_roboflow.py
Downloads Roboflow datasets into ml/datasets/raw/roboflow/
- OnionSpoilageDetection (~1690 images)
- chandrajith-j/onions-quality-analysis (209 images)
"""

import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("download_roboflow")


def load_env_file(env_path=".env"):
    """Loads key-value pairs from .env without requiring python-dotenv."""
    path = Path(env_path)
    if not path.is_file():
        return
    logger.info(f"Loading environment variables from {path.resolve()}...")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k and k not in os.environ:
                    os.environ[k] = v


def download_dataset(rf, workspace_name, project_name, version_num, output_dir, format_type="yolov11"):
    """Downloads a dataset version into output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Connecting to Roboflow workspace '{workspace_name}', project '{project_name}', version {version_num}...")
    
    project = rf.workspace(workspace_name).project(project_name)
    version = project.version(version_num)
    
    logger.info(f"Downloading format '{format_type}' to '{output_dir}'...")
    dataset = version.download(model_format=format_type, location=str(output_dir))
    logger.info(f"Successfully downloaded to: {dataset.location}")
    return dataset


def main():
    # 1. Load environment variables
    load_env_file(".env")
    
    api_key = os.environ.get("ROBOFLOW_API_KEY")
    if not api_key:
        logger.error("=" * 60)
        logger.error("MISSING ROBOFLOW_API_KEY!")
        logger.error("Roboflow requires an API key to download datasets.")
        logger.error("Please add your key to `.env`:")
        logger.error("    ROBOFLOW_API_KEY=your_key_here")
        logger.error("Or set it in your environment:")
        logger.error("    $env:ROBOFLOW_API_KEY='your_key_here'")
        logger.error("You can get a free API key at: https://app.roboflow.com/settings/api")
        logger.error("=" * 60)
        sys.exit(1)
        
    try:
        from roboflow import Roboflow
    except ImportError:
        logger.error("The `roboflow` package is not installed. Run: pip install roboflow")
        sys.exit(1)

    rf = Roboflow(api_key=api_key)
    base_dest = Path("ml/datasets/raw/roboflow")
    base_dest.mkdir(parents=True, exist_ok=True)

    # Dataset 1: OnionSpoilageDetection
    logger.info("--- [1/2] Processing OnionSpoilageDetection ---")
    dest_d1 = base_dest / "OnionSpoilageDetection"
    try:
        # Primary workspace/project on Universe
        download_dataset(
            rf=rf,
            workspace_name="onionspoilagedetection",
            project_name="onion_spoilage_detection",
            version_num=1,
            output_dir=dest_d1,
            format_type="yolov11"
        )
    except Exception as e:
        logger.warning(f"Could not download from 'onionspoilagedetection/onion_spoilage_detection': {e}")
        logger.info("Attempting fallback workspace 'kush-maurya/onions-r8sei-kuogb'...")
        try:
            download_dataset(
                rf=rf,
                workspace_name="kush-maurya",
                project_name="onions-r8sei-kuogb",
                version_num=1,
                output_dir=dest_d1,
                format_type="yolov11"
            )
        except Exception as e2:
            logger.error(f"Failed fallback download for OnionSpoilageDetection: {e2}")

    # Dataset 2: chandrajith-j/onions-quality-analysis
    logger.info("--- [2/2] Processing chandrajith-j/onions-quality-analysis ---")
    dest_d2 = base_dest / "onions-quality-analysis"
    try:
        download_dataset(
            rf=rf,
            workspace_name="chandrajith-j",
            project_name="onions-quality-analysis",
            version_num=1,
            output_dir=dest_d2,
            format_type="yolov11"
        )
    except Exception as e:
        logger.error(f"Failed to download 'chandrajith-j/onions-quality-analysis': {e}")

    logger.info("Roboflow download pipeline finished.")


if __name__ == "__main__":
    main()
