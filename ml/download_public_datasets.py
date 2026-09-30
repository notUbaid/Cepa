import os
import sys
import json
import requests
import zipfile
import shutil
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("download_datasets")

def download_file(url, dest_path):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    total_size = int(response.headers.get('content-length', 0))
    block_size = 8192
    
    with open(dest_path, 'wb') as f:
        downloaded = 0
        for data in response.iter_content(block_size):
            f.write(data)
            downloaded += len(data)
            if total_size > 0:
                percent = int(100 * downloaded / total_size)
                if percent % 10 == 0:
                    sys.stdout.write(f"\rDownloading... {percent}%")
                    sys.stdout.flush()
    sys.stdout.write("\n")

def download_mendeley():
    # DOI: 10.17632/42bcyncfhy.2
    dataset_id = "42bcyncfhy"
    version = "2"
    url = f"https://data.mendeley.com/public-api/datasets/{dataset_id}/files?version={version}"
    
    dest_dir = Path("ml/datasets/raw/mendeley")
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Fetching Mendeley Data from {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        files = response.json()
        
        for file_info in files:
            filename = file_info.get("filename", "")
            download_url = file_info.get("content_details", {}).get("download_url")
            
            # We only want bulb images, if it's a zip we might need to extract later
            if download_url:
                file_path = dest_dir / filename
                if not file_path.exists():
                    logger.info(f"Downloading {filename}...")
                    download_file(download_url, file_path)
                
                # If it's a zip, extract it
                if filename.endswith(".zip"):
                    extract_dir = dest_dir / filename.replace(".zip", "")
                    if not extract_dir.exists():
                        logger.info(f"Extracting {filename}...")
                        with zipfile.ZipFile(file_path, 'r') as zip_ref:
                            zip_ref.extractall(extract_dir)
                            
        logger.info("Mendeley dataset downloaded and extracted.")
    except Exception as e:
        logger.error(f"Failed to fetch Mendeley dataset: {e}")

def download_harvard():
    # DOI: 10.7910/DVN/ZNPAC8
    persistent_id = "doi:10.7910/DVN/ZNPAC8"
    url = f"https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId={persistent_id}"
    
    dest_dir = Path("ml/datasets/raw/harvard_dataverse")
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Fetching Harvard Dataverse from {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json().get("data", {})
        
        files = data.get("latestVersion", {}).get("files", [])
        
        for file_info in files:
            file_id = file_info.get("dataFile", {}).get("id")
            filename = file_info.get("dataFile", {}).get("filename")
            
            if file_id and filename:
                download_url = f"https://dataverse.harvard.edu/api/access/datafile/{file_id}"
                file_path = dest_dir / filename
                if not file_path.exists():
                    logger.info(f"Downloading {filename}...")
                    download_file(download_url, file_path)
                    
                if filename.endswith(".zip"):
                    extract_dir = dest_dir / filename.replace(".zip", "")
                    if not extract_dir.exists():
                        logger.info(f"Extracting {filename}...")
                        with zipfile.ZipFile(file_path, 'r') as zip_ref:
                            zip_ref.extractall(extract_dir)
                            
        logger.info("Harvard Dataverse dataset downloaded and extracted.")
    except Exception as e:
        logger.error(f"Failed to fetch Harvard Dataverse dataset: {e}")

if __name__ == "__main__":
    download_mendeley()
    download_harvard()
