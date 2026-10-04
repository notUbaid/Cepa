import torch
from PIL import Image
from ram.models import ram
import torchvision.transforms as transforms
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ml_test_ram")

def test_ram(image_path: str):
    logger.info("Initializing RAM++ test...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"RAM++ loaded successfully Device: {device}")
    
    # Needs the checkpoint downloaded
    checkpoint_path = "ml/models/ram/ram_swin_large_14m.pth"
    import os
    if not os.path.exists(checkpoint_path):
        logger.info(f"Downloading checkpoint to {checkpoint_path}...")
        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
        import urllib.request
        url = "https://huggingface.co/spaces/xinyu1205/Recognize_Anything-Tag2Text/resolve/main/ram_swin_large_14m.pth"
        urllib.request.urlretrieve(url, checkpoint_path)
    
    # Load model
    logger.info("Loading model weights...")
    model = ram(pretrained=checkpoint_path, image_size=384, vit='swin_l')
    model.eval()
    model.to(device)
    
    # Prepare image
    transform = transforms.Compose([
        transforms.Resize((384, 384)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    logger.info(f"Image: {image_path}")
    image = Image.open(image_path).convert('RGB')
    image_tensor = transform(image).unsqueeze(0).to(device)
    
    # Inference
    with torch.no_grad():
        tags, tags_chinese = model.generate_tag(image_tensor)
        
    if tags:
        tag_list = [t.strip().lower() for t in tags[0].split('|')]
        logger.info(f"Detected tags:")
        for tag in tag_list:
            logger.info(f"  - {tag}")
    else:
        logger.info("Detected tags: None")

if __name__ == "__main__":
    test_crop = "cv_tools/dataset/real_onions/crops/rotten/real_rotten_File_Insect_pests_of_farm__garden_and_orchard__1912___14591969157__17.jpg"
    if len(sys.argv) > 1:
        test_crop = sys.argv[1]
    test_ram(test_crop)
