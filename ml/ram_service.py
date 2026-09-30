import os
import urllib.request
import torch
import torchvision.transforms as transforms
from PIL import Image
import logging
from pathlib import Path
import cv2

logger = logging.getLogger(__name__)

class RAMService:
    def __init__(self, model_type="swin_large", image_size=384, checkpoints_dir="ml/models/ram"):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.image_size = image_size
        self.model_type = model_type
        self.checkpoints_dir = Path(checkpoints_dir)
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path = self.checkpoints_dir / "ram_swin_large_14m.pth"
        self.model = None
        
        self.transform = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def _download_checkpoint(self):
        url = "https://huggingface.co/spaces/xinyu1205/Recognize_Anything-Tag2Text/resolve/main/ram_swin_large_14m.pth"
        if not self.checkpoint_path.exists():
            logger.info(f"Downloading RAM++ checkpoint to {self.checkpoint_path}. This may take a while (approx 1.5GB)...")
            try:
                urllib.request.urlretrieve(url, str(self.checkpoint_path))
                logger.info("Download complete.")
            except Exception as e:
                logger.error(f"Failed to download RAM++ checkpoint: {e}")

    def load_model(self):
        try:
            from ram.models import ram
        except ImportError:
            logger.error("RAM++ is not installed. Run: pip install git+https://github.com/xinyu1205/recognize-anything.git")
            return False

        self._download_checkpoint()
        
        if not self.checkpoint_path.exists():
            logger.error("RAM++ checkpoint not found.")
            return False

        logger.info(f"Loading RAM++ model on {self.device}...")
        try:
            # Load RAM model
            self.model = ram(pretrained=str(self.checkpoint_path),
                             image_size=self.image_size,
                             vit='swin_l')
            self.model.eval()
            self.model.to(self.device)
            logger.info("RAM++ model loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"Error loading RAM++ model: {e}")
            return False

    def recognize_tags(self, image_bgr) -> list[str]:
        """
        Takes a BGR image (from cv2), converts to RGB, and returns a list of semantic tags.
        """
        if self.model is None:
            logger.warning("RAM++ model is not loaded. Returning empty tags.")
            return []

        # Convert BGR to RGB PIL Image
        img_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(img_rgb)
        
        image_tensor = self.transform(image).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            tags, tags_chinese = self.model.generate_tag(image_tensor)
        
        if tags and len(tags) > 0:
            # Tags are typically returned as a string separated by ' | '
            tag_list = [t.strip().lower() for t in tags[0].split('|')]
            return tag_list
        return []
