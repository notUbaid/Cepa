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
