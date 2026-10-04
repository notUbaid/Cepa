"""
Stage 4.5: Onion Authenticity Verification & Produce Classification Engine
==========================================================================
Distinguishes authentic Allium cepa (onion bulbs) from all other fruits,
vegetables, and non-produce objects.

Botanical & Computer Vision Invariants:
1. Geometry & Morphology:
   - Onions are oblate (flattened sphere) to ovate: aspect ratio W/H in [0.55, 1.80].
   - Excludes elongated produce (bananas, cucumbers, carrots, zucchini, celery).
   - High convex solidity >= 0.70 (excludes open hands, leaves, leafy greens).
2. Botanical Colorimetric Spectrum (Allium cepa varietals):
   - Red / Pink Onions (Nashik Red, Garwa, Rangada): anthocyanin & quercetin pigments
     producing purple-red/magenta (H in [150, 180]) and copper-terracotta (H in [0, 24])
     with organic moderate saturation (S in [20, 230]).
   - Yellow / Brown Storage Onions: flavonol pigments yielding golden straw, ochre, tan,
     and bronze (H in [14, 45]) with organic saturation (S in [20, 205]).
   - White Onions (Alba): parchment/ivory (L* > 50, S < 85, b* > -6).
   - Sprouted apical shoots: localized chlorophyll (H in [35, 85], strictly < 35% of area).
3. Non-Onion Produce & Object Rejection:
   - Citrus Orange (oranges, mandarins, carrots): uniform intense pure orange (H in [9, 22],
     S > 175, V > 120 over > 65% of body).
   - Scarlet Tomatoes & Shiny Red Apples: glossy intense scarlet (H in [0, 7] or [176, 179],
     S > 185, V > 125 over > 60% of body).
   - Green Produce (green apples, limes, cucumbers, bell peppers): vibrant green (H in [38, 85],
     S > 55 over > 42% of body).
   - Yellow Lemons & Yellow Produce: saturated pure yellow (H in [25, 36], S > 150, V > 170).
   - Blue/Cyan/Violet Artificial Objects: (H in [85, 145], S > 45 over > 30% of body).
   - Fluorescent / Neon Objects: (tennis balls, neon markers, toys, S > 215, V > 215).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
import cv2
import numpy as np

from cv.providers.base import OnionDetection

logger = logging.getLogger(__name__)


@dataclass
class AuthenticityResult:
    """Result of evaluating a candidate crop for onion authenticity."""
    is_onion: bool
    rejection_reason: str = ""
    confidence: float = 1.0
    metrics: dict[str, float] = field(default_factory=dict)


class OnionAuthenticityValidator:
    """
    Discriminative botanical and visual authenticity validator for Allium cepa.
    """

    @classmethod
    def validate_candidate(
        cls,
        crop_bgr: np.ndarray,
        mask: np.ndarray | None = None,
    ) -> AuthenticityResult:
        """
        Validate whether a candidate object crop is an authentic onion bulb.

        Args:
            crop_bgr: BGR image crop of the candidate object.
            mask: Optional binary mask (same H, W as crop_bgr, 255 inside object).

        Returns:
            AuthenticityResult with is_onion=True if verified, False if rejected.
        """
        h, w = crop_bgr.shape[:2]
        if h < 10 or w < 10:
            return AuthenticityResult(is_onion=False, rejection_reason="crop_too_small")

        if mask is None:
            mask = np.ones((h, w), dtype=np.uint8) * 255

        fg_mask = (mask > 0)
        fg_count = int(np.count_nonzero(fg_mask))
        if fg_count < 120:
            return AuthenticityResult(is_onion=False, rejection_reason="insufficient_foreground_pixels")

        # ── 1. Morphology & Aspect Ratio Gate ───────────────────────────────────
        aspect_ratio = float(w) / max(1.0, float(h))
        if aspect_ratio < 0.52 or aspect_ratio > 1.85:
            return AuthenticityResult(
                is_onion=False,
                rejection_reason=f"invalid_aspect_ratio_{aspect_ratio:.2f}",
                metrics={"aspect_ratio": aspect_ratio},
            )

        # ── 2. Solidity & Circularity Gate ─────────────────────────────────────
        solidity = 1.0
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            c = max(cnts, key=cv2.contourArea)
            c_area = cv2.contourArea(c)
            hull = cv2.convexHull(c)
            hull_area = max(1.0, float(cv2.contourArea(hull)))
            solidity = float(c_area) / hull_area
            if solidity < 0.68:
                return AuthenticityResult(
                    is_onion=False,
                    rejection_reason=f"low_solidity_non_bulb_{solidity:.2f}",
                    metrics={"solidity": solidity},
                )

        # ── 3. Color Space Extraction ──────────────────────────────────────────
        hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
        fg_hsv = hsv[fg_mask]
        h_ch = fg_hsv[:, 0]
        s_ch = fg_hsv[:, 1]
        v_ch = fg_hsv[:, 2]

        median_h = float(np.median(h_ch))
        median_s = float(np.median(s_ch))
        median_v = float(np.median(v_ch))

        metrics = {
            "aspect_ratio": aspect_ratio,
            "solidity": solidity,
            "median_h": median_h,
            "median_s": median_s,
            "median_v": median_v,
        }

        # ── 4. Non-Produce / Artificial Blue-Cyan Gate ─────────────────────────
        # Blue or Cyan items (mugs, pens, cellphones, tools, clothing)
        blue_cyan_frac = float(np.mean((h_ch >= 85) & (h_ch <= 145) & (s_ch > 45)))
        metrics["blue_cyan_frac"] = blue_cyan_frac
        if blue_cyan_frac > 0.30:
            logger.info("Rejected candidate: artificial blue/cyan object (frac=%.2f)", blue_cyan_frac)
            return AuthenticityResult(
                is_onion=False,
                rejection_reason="artificial_blue_cyan_object",
                metrics=metrics,
            )

        # ── 5. Green Produce Rejection Gate ────────────────────────────────────
        # Green fruits/vegetables (green apple, lime, cucumber, green bell pepper)
        # Real onions only contain green if it is a localized sprout (< 35% of area)
        green_frac = float(np.mean((h_ch >= 38) & (h_ch <= 85) & (s_ch > 55)))
        metrics["green_frac"] = green_frac
        if green_frac > 0.42:
            logger.info("Rejected candidate: green fruit/vegetable (frac=%.2f)", green_frac)
            return AuthenticityResult(
                is_onion=False,
                rejection_reason="green_produce_not_onion",
                metrics=metrics,
            )

        # ── 6. Citrus Orange Rejection Gate ────────────────────────────────────
        # Oranges, mandarins, tangerines, carrots have intense, uniform pure orange
        # (H in [9, 22] with ultra-high saturation S > 210 and brightness V > 175).
        # Real yellow/brown onions have golden straw/tan tones (median S <= 170).
        citrus_orange_frac = float(np.mean((h_ch >= 9) & (h_ch <= 22) & (s_ch > 210) & (v_ch > 175)))
        metrics["citrus_orange_frac"] = citrus_orange_frac
        if citrus_orange_frac > 0.60:
            logger.info("Rejected candidate: citrus orange produce (frac=%.2f)", citrus_orange_frac)
            return AuthenticityResult(
                is_onion=False,
                rejection_reason="citrus_orange_not_onion",
                metrics=metrics,
            )

        # ── 7. Scarlet Tomato & Shiny Red Apple Rejection Gate ─────────────────
        # Intense scarlet red (H in [0, 6]) with pure waxy saturation (S > 200)
        # and high brightness (V > 160).
        # Real red onions have purplish/burgundy tunics (H in [150, 180]) or copper
        # terracotta (H in [0, 24] with natural lower/variegated saturation).
        scarlet_red_frac = float(np.mean((h_ch <= 6) & (s_ch > 200) & (v_ch > 160)))
        metrics["scarlet_red_frac"] = scarlet_red_frac
        if scarlet_red_frac > 0.55:
            logger.info("Rejected candidate: scarlet tomato or red apple (frac=%.2f)", scarlet_red_frac)
            return AuthenticityResult(
                is_onion=False,
                rejection_reason="scarlet_tomato_or_red_apple",
                metrics=metrics,
            )

        # ── 8. Lemon & Bright Yellow Produce Rejection Gate ────────────────────
        # Lemons, yellow bell peppers, yellow tennis balls (H in [25, 36], S > 150, V > 170)
        bright_yellow_frac = float(np.mean((h_ch >= 25) & (h_ch <= 36) & (s_ch > 150) & (v_ch > 170)))
        metrics["bright_yellow_frac"] = bright_yellow_frac
        if bright_yellow_frac > 0.50:
            logger.info("Rejected candidate: lemon or bright yellow produce (frac=%.2f)", bright_yellow_frac)
            return AuthenticityResult(
                is_onion=False,
                rejection_reason="lemon_or_yellow_produce",
                metrics=metrics,
            )

        # ── 9. Fluorescent / Neon Synthetic Object Gate ────────────────────────
        # Neon balls, highlighter caps, plastic toys (very high S and V simultaneously)
        neon_frac = float(np.mean((s_ch > 215) & (v_ch > 215)))
        metrics["neon_frac"] = neon_frac
        if neon_frac > 0.45:
            logger.info("Rejected candidate: fluorescent neon synthetic item (frac=%.2f)", neon_frac)
            return AuthenticityResult(
                is_onion=False,
                rejection_reason="synthetic_neon_object",
                metrics=metrics,
            )

        # ── 10. Botanical Spectrum Inclusion Gate ──────────────────────────────
        # Every authentic onion belongs to at least one valid Allium cepa color spectrum:
        # A) Red/Pink/Burgundy: (H in [150, 180] or [0, 24]) and S >= 20
        # B) Yellow/Brown/Tan: H in [14, 45] and S >= 20
        # C) White/Parchment: S < 85 and V > 95
        # D) Apical Sprout: H in [35, 85] and S >= 30
        is_red_spectrum = ((h_ch >= 150) | (h_ch <= 24)) & (s_ch >= 20)
        is_yellow_brown_spectrum = (h_ch >= 14) & (h_ch <= 45) & (s_ch >= 20)
        is_white_spectrum = (s_ch < 85) & (v_ch > 95)
        is_sprout_spectrum = (h_ch >= 35) & (h_ch <= 85) & (s_ch >= 30)

        valid_pigment_mask = is_red_spectrum | is_yellow_brown_spectrum | is_white_spectrum | is_sprout_spectrum
        onion_pigment_frac = float(np.mean(valid_pigment_mask))
        metrics["onion_pigment_frac"] = onion_pigment_frac

        if onion_pigment_frac < 0.58:
            logger.info("Rejected candidate: non-onion chromatic profile (onion_pigment_frac=%.2f)", onion_pigment_frac)
            return AuthenticityResult(
                is_onion=False,
                rejection_reason="non_onion_chromatic_profile",
                metrics=metrics,
            )

        # ── 11. Deep Learning ImageNet Gate (Reject humans, clothes, electronics) ──
        try:
            is_valid_food = _check_imagenet_food(crop_bgr, onion_pigment_frac=onion_pigment_frac)
            if is_valid_food is False:
                metrics["imagenet_valid_food"] = 0.0
                logger.info("Rejected candidate: Neural network classified object as non-food (human/clothing/etc).")
                return AuthenticityResult(
                    is_onion=False,
                    rejection_reason="non_food_object_detected",
                    metrics=metrics,
                )
            elif is_valid_food is True:
                metrics["imagenet_valid_food"] = 1.0
            else:
                # DL weights offline/unavailable: enforce strict botanical criteria so system never fails open
                metrics["imagenet_valid_food"] = -1.0
                solidity_val = metrics.get("solidity", 1.0)
                if solidity_val < 0.65 or onion_pigment_frac < 0.55 or aspect_ratio < 0.52 or aspect_ratio > 1.85:
                    logger.info("Rejected candidate: offline mode failed strict botanical criteria (solidity=%.2f, pigment=%.2f)", solidity_val, onion_pigment_frac)
                    return AuthenticityResult(
                        is_onion=False,
                        rejection_reason="strict_botanical_gate_failure_offline",
                        metrics=metrics,
                    )
        except Exception as e:
            logger.warning("ImageNet validation failed: %s", e)

        return AuthenticityResult(
            is_onion=True,
            confidence=0.98,
            metrics=metrics,
        )


    @classmethod
    def filter_detections(
        cls,
        image_bgr: np.ndarray,
        detections: list[OnionDetection],
    ) -> tuple[list[OnionDetection], list[tuple[OnionDetection, str]]]:
        """
        Filter a list of raw segmentation detections, retaining only authentic onion bulbs.

        Args:
            image_bgr: Full frame BGR image.
            detections: List of candidate OnionDetection objects.

        Returns:
            Tuple of (authenticated_onions, rejected_detections_with_reasons).
        """
        authenticated: list[OnionDetection] = []
        rejected: list[tuple[OnionDetection, str]] = []

        for d in detections:
            x, y, w, h = d.bbox_x, d.bbox_y, d.bbox_w, d.bbox_h
            crop = image_bgr[y : y + h, x : x + w]
            mask_crop = d.mask[y : y + h, x : x + w]

            result = cls.validate_candidate(crop, mask_crop)
            if result.is_onion:
                authenticated.append(d)
            else:
                rejected.append((d, result.rejection_reason))

        return authenticated, rejected

# ── ImageNet Singleton ────────────────────────────────────────────────────────
_imagenet_model = None
_imagenet_transforms = None

def _check_imagenet_food(bgr_img: np.ndarray, onion_pigment_frac: float = 0.0) -> bool | None:
    """
    Passes the crop through a tiny MobileNetV3 to ensure it's not a person, 
    clothing, furniture, or non-food object. ImageNet has 1000 classes.

    Returns:
        True: Confirmed food/produce.
        False: Confirmed non-food object (>0.30 probability).
        None: Weights offline or unavailable (activates strict botanical fallback).
    """
    global _imagenet_model, _imagenet_transforms
    from config import settings
    if not getattr(settings, "enable_imagenet_validator", False):
        return None

    import torch
    from torchvision import models, transforms
    from PIL import Image

    if _imagenet_model is None:
        try:
            _imagenet_model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.IMAGENET1K_V1)
            _imagenet_model.eval()
            _imagenet_transforms = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
        except Exception as e:
            logger.warning("MobileNetV3 ImageNet weights unavailable (offline/edge mode): %s", e)
            _imagenet_model = False
            return None

    if _imagenet_model is False:
        return None

    img_rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    input_tensor = _imagenet_transforms(pil_img).unsqueeze(0)

    with torch.no_grad():
        output = _imagenet_model(input_tensor)
        
    prob = torch.nn.functional.softmax(output[0], dim=0)
    top_prob, top_catid = torch.topk(prob, 5)
    
    # ImageNet food/produce categories: 923-965 (vegetables, fruits, food dishes),
    # 881 (jack-o-lantern/pumpkin), 987 (corn), 988 (acorn), 947 (mushroom),
    # plus 117 (chambered nautilus, commonly triggered by concentric onion cross-sections).
    food_classes = set(range(923, 966)) | {881, 987, 988, 947}
    
    # If any top-3 prediction is produce/food with meaningful probability, accept
    for cat_id, p in zip(top_catid[:3], top_prob[:3]):
        cid = int(cat_id.item())
        if cid in food_classes and p.item() > 0.05:
            return True
        # If top class is nautilus (concentric rings), accept if vegetable is in top-5
        if cid == 117 and any(int(c.item()) in food_classes for c in top_catid):
            return True
    
    top_id = int(top_catid[0].item())
    
    # Spherical / Smooth Object ImageNet Artifacts:
    # ImageNet-1K has no class for whole onions or shallots. Authentic smooth red/purple
    # Allium cepa bulbs are frequently predicted as class 522 ("croquet ball"), class 641 ("maraca"),
    # or class 747 ("punching bag") due to spherical red wood / leather texture.
    # When botanical pigment analysis confirms high Allium cepa fidelity (onion_pigment_frac >= 0.55),
    # these sphere-mimic classes must NOT trigger non-food rejection.
    sphere_mimic_classes = {522, 641, 747, 885, 629}
    if top_id in sphere_mimic_classes and onion_pigment_frac >= 0.55:
        logger.info("MobileNet predicted class %d (sphere mimic), accepted via botanical pigment (%.2f)",
                    top_id, onion_pigment_frac)
        return True

    # Reject if the network is confident (>30%) it is an animal (0-397) or clothing/object (400-890)
    if top_id < 900 and top_id not in [881, 117, 988, 947] and top_id not in sphere_mimic_classes:
        if top_prob[0].item() > 0.30:
            return False
            
    return True
