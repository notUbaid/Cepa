"""
Synthetic Test Image Generator

Generates a realistic synthetic test image of an onion spread with:
1. The ChArUco board rendered into a corner/side of the frame
2. Multiple synthetic onion bulbs (ellipses with onion skin hues and textures)
   - Some in Grade A range (45-65mm)
   - Some small/URS (35-45mm)
   - Some defective (simulated cuts, dark spots)
3. Good lighting and sharp contrast to pass the Stage 1 Image Quality Gate

Usage:
  python cv_tools/generate_synthetic_sample.py
"""
from pathlib import Path
import cv2
import numpy as np

OUT_DIR = Path(__file__).parent / "test_data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BOARD_PNG = Path(__file__).parent / "calibration_board" / "charuco_board_7x5_40mm.png"


def generate_synthetic_onion_spread() -> Path:
    # Canvas: 1800 x 1400 (aspect ~4:3, > 1000px resolution check)
    canvas_w = 1800
    canvas_h = 1400

    # Background: clean matte light grey/beige inspection table (RGB ~ 210, 205, 195)
    # Mean lum around 140-160 -> well within [40, 215] quality range
    table = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)
    table[:, :] = [190, 200, 205]  # BGR

    # Add subtle table grain texture
    noise = np.random.normal(0, 4, (canvas_h, canvas_w, 3)).astype(np.int16)
    table = np.clip(table.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # 1. Overlay ChArUco board in top-right or top-left
    # Scale board image so that 40mm square ≈ 70-80 pixels in our camera view (scale ~0.55 mm/px)
    if BOARD_PNG.exists():
        board_img = cv2.imread(str(BOARD_PNG))
        # Board is 7x5 squares = 280x200mm.
        # At 0.55 mm/px, board size in image ≈ 509 x 363 pixels
        target_w = 510
        target_h = int(board_img.shape[0] * (target_w / board_img.shape[1]))
        board_scaled = cv2.resize(board_img, (target_w, target_h), interpolation=cv2.INTER_AREA)

        # Place at top-left: x=80, y=80
        bx, by = 80, 80
        table[by : by + target_h, bx : bx + target_w] = board_scaled

        # Draw a small shadow / border around board
        cv2.rectangle(table, (bx - 2, by - 2), (bx + target_w + 2, by + target_h + 2), (140, 140, 140), 2)

    # 2. Draw synthetic onion bulbs
    # Scale: ~0.55 mm/px -> 50mm onion ≈ 91 px diameter (radius ~45)
    # 38mm onion ≈ 69 px diameter
    # 60mm onion ≈ 109 px diameter
    np.random.seed(42)

    onion_specs = [
        # (center_x, center_y, diam_mm, color_bgr, defect_type)
        (750, 400, 52.0, (40, 65, 160), "healthy"),       # Grade A reddish-purple
        (920, 380, 58.0, (50, 75, 175), "healthy"),       # Grade A
        (1100, 430, 48.0, (45, 70, 165), "healthy"),      # Grade A
        (780, 620, 62.0, (48, 72, 170), "healthy"),       # Grade A
        (970, 600, 54.0, (42, 68, 162), "healthy"),       # Grade A
        (1160, 630, 50.0, (46, 70, 168), "healthy"),      # Grade A
        (820, 850, 40.0, (55, 80, 180), "healthy"),       # URS (small)
        (1000, 830, 42.0, (50, 78, 178), "damaged"),      # URS (damaged)
        (1200, 870, 53.0, (30, 40, 80), "rotten"),        # Rotten (dark decay)
        (1350, 480, 56.0, (60, 130, 80), "sprouted"),     # Sprouted (green shoot)
        (1400, 750, 32.0, (55, 80, 175), "undersized"),   # Undersized (<35mm)
        (700, 1100, 55.0, (45, 70, 165), "healthy"),      # Grade A
        (900, 1120, 60.0, (48, 72, 170), "healthy"),      # Grade A
        (1120, 1100, 52.0, (42, 68, 162), "healthy"),     # Grade A
        (1320, 1080, 48.0, (46, 70, 168), "healthy"),     # Grade A
    ]

    mm_per_px = 0.55

    for cx, cy, d_mm, base_color, defect in onion_specs:
        radius_px = int((d_mm / mm_per_px) / 2.0)
        axes = (radius_px, int(radius_px * np.random.uniform(0.92, 1.08)))
        angle = np.random.randint(0, 180)

        # Draw drop shadow
        cv2.ellipse(table, (cx + 8, cy + 8), axes, angle, 0, 360, (140, 150, 155), -1)

        # Draw bulb body with gradient/texture
        cv2.ellipse(table, (cx, cy), axes, angle, 0, 360, base_color, -1)

        # Add onion skin concentric rings / texture
        for r_ratio in [0.8, 0.6, 0.4, 0.2]:
            sub_axes = (int(axes[0] * r_ratio), int(axes[1] * r_ratio))
            ring_color = tuple(min(255, int(c * (1.0 + (1 - r_ratio) * 0.2))) for c in base_color)
            cv2.ellipse(table, (cx, cy), sub_axes, angle, 0, 360, ring_color, 2)

        # Draw root / tip accent
        tip_x = int(cx + axes[0] * 0.9 * np.cos(np.radians(angle)))
        tip_y = int(cy + axes[0] * 0.9 * np.sin(np.radians(angle)))
        cv2.circle(table, (tip_x, tip_y), 4, (30, 40, 60), -1)

        # Defect markers
        if defect == "damaged":
            # Cut or bruise line
            cv2.line(table, (cx - 15, cy - 10), (cx + 15, cy + 10), (20, 30, 70), 3)
        elif defect == "rotten":
            # Dark rotting patch
            cv2.circle(table, (cx + 8, cy - 5), int(radius_px * 0.45), (15, 20, 30), -1)
        elif defect == "sprouted":
            # Green shoot protruding
            shoot_end = (tip_x + 30, tip_y - 25)
            cv2.line(table, (tip_x, tip_y), shoot_end, (30, 180, 50), 5)
            cv2.circle(table, shoot_end, 5, (40, 210, 60), -1)

    out_path = OUT_DIR / "synthetic_onion_spread_sample.jpg"
    cv2.imwrite(str(out_path), table, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"Generated synthetic test image: {out_path} ({canvas_w}x{canvas_h} px)")
    return out_path


if __name__ == "__main__":
    generate_synthetic_onion_spread()
