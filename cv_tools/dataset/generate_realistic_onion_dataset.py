"""
Photorealistic Onion Segmentation Dataset Generator
Generates realistic Indian mandi scenes with authentic bulb cutouts,
procedural mandi backgrounds (burlap jute, wood, blue tarp, concrete, tray),
and pixel-perfect occlusion-aware polygon ground truth.
"""
from pathlib import Path
import random
import cv2
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CUTOUTS_DIR = ROOT_DIR / "cv_tools" / "dataset" / "clean_cutouts"
OUTPUT_DIR = ROOT_DIR / "cv_tools" / "dataset" / "onion_seg_real"

def make_background(bg_type: str, size: int = 640) -> np.ndarray:
    if bg_type == "burlap":
        # Woven burlap jute texture
        base = np.full((size, size, 3), [135, 170, 195], dtype=np.uint8)
        x = np.arange(size)
        y = np.arange(size)
        xx, yy = np.meshgrid(x, y)
        weave_h = (np.sin(xx * 0.75) * 16).astype(np.int16)
        weave_v = (np.sin(yy * 0.75) * 16).astype(np.int16)
        noise = np.random.normal(0, 7, (size, size, 3)).astype(np.int16)
        return np.clip(base.astype(np.int16) + weave_h[:, :, None] + weave_v[:, :, None] + noise, 0, 255).astype(np.uint8)

    elif bg_type == "wood":
        # Weathered wooden sorting table
        base = np.full((size, size, 3), [85, 125, 165], dtype=np.uint8)
        y = np.arange(size)
        grain = (np.sin(y * 0.12) * 22 + np.sin(y * 0.04) * 32).astype(np.int16)
        noise = np.random.normal(0, 6, (size, size, 3)).astype(np.int16)
        return np.clip(base.astype(np.int16) + grain[:, None, None] + noise, 0, 255).astype(np.uint8)

    elif bg_type == "blue_tarp":
        # Blue poly tarp with diagonal folds
        base = np.full((size, size, 3), [175, 75, 20], dtype=np.uint8)
        x = np.arange(size)
        y = np.arange(size)
        xx, yy = np.meshgrid(x, y)
        crease = (np.sin((xx + yy) * 0.04) * 20).astype(np.int16)
        noise = np.random.normal(0, 8, (size, size, 3)).astype(np.int16)
        return np.clip(base.astype(np.int16) + crease[:, :, None] + noise, 0, 255).astype(np.uint8)

    elif bg_type == "concrete":
        # Mandi concrete floor
        base = np.full((size, size, 3), [160, 165, 170], dtype=np.uint8)
        noise = np.random.normal(0, 14, (size, size, 3)).astype(np.int16)
        return np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    else:
        # Clean white/light gray inspection tray
        base = np.full((size, size, 3), [225, 230, 235], dtype=np.uint8)
        noise = np.random.normal(0, 4, (size, size, 3)).astype(np.int16)
        return np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)


def generate_dataset(num_train: int = 80, num_val: int = 20, img_size: int = 640):
    for split in ["train", "val"]:
        (OUTPUT_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)

    cutout_files = list(CUTOUTS_DIR.glob("*.png"))
    if not cutout_files:
        raise RuntimeError(f"No cutouts found in {CUTOUTS_DIR}")

    print(f"Loaded {len(cutout_files)} clean authentic onion cutouts.")
    total_scenes = num_train + num_val
    bg_types = ["burlap", "wood", "blue_tarp", "concrete", "tray"]

    for scene_idx in range(total_scenes):
        split = "train" if scene_idx < num_train else "val"
        filename = f"mandi_scene_{scene_idx:04d}"

        # Choose background
        bg_choice = random.choice(bg_types)
        canvas = make_background(bg_choice, size=img_size)

        # Decide cluster complexity
        # 10% single bulb, 30% medium spread (4-8 bulbs), 60% dense cluster (10-18 bulbs)
        r_type = random.random()
        if r_type < 0.10:
            n_bulbs = random.randint(1, 2)
        elif r_type < 0.40:
            n_bulbs = random.randint(4, 8)
        else:
            n_bulbs = random.randint(10, 18)

        sampled_cutouts = random.choices(cutout_files, k=n_bulbs)

        # Data structures to track instances and occlusions
        # We place bulbs back-to-front. A bulb placed later occludes bulbs placed earlier.
        placed_instances = []

        for b_idx, cp in enumerate(sampled_cutouts):
            rgba = cv2.imread(str(cp), cv2.IMREAD_UNCHANGED)
            if rgba is None or rgba.shape[2] != 4:
                continue

            h_orig, w_orig = rgba.shape[:2]
            # Random scaling (Goli 55px to Jumbo 180px)
            target_dim = random.randint(60, 175)
            scale = target_dim / max(h_orig, w_orig)
            nw = max(15, int(w_orig * scale))
            nh = max(15, int(h_orig * scale))
            rgba_scaled = cv2.resize(rgba, (nw, nh), interpolation=cv2.INTER_LINEAR)

            # Random 360-degree rotation & slight shear
            angle = random.uniform(0, 360)
            M = cv2.getRotationMatrix2D((nw / 2, nh / 2), angle, 1.0)
            cos = np.abs(M[0, 0])
            sin = np.abs(M[0, 1])
            bound_w = int((nh * sin) + (nw * cos))
            bound_h = int((nh * cos) + (nw * sin))
            M[0, 2] += (bound_w / 2) - nw / 2
            M[1, 2] += (bound_h / 2) - nh / 2

            rgba_rot = cv2.warpAffine(
                rgba_scaled, M, (bound_w, bound_h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0, 0),
            )

            # Random slight color jitter (warm/cool shift)
            b, g, r, a = cv2.split(rgba_rot)
            b_shift = random.randint(-12, 12)
            g_shift = random.randint(-8, 8)
            r_shift = random.randint(-15, 15)
            b = np.clip(b.astype(np.int16) + b_shift, 0, 255).astype(np.uint8)
            g = np.clip(g.astype(np.int16) + g_shift, 0, 255).astype(np.uint8)
            r = np.clip(r.astype(np.int16) + r_shift, 0, 255).astype(np.uint8)
            bulb_rgb = cv2.merge([b, g, r])

            # Random placement on canvas
            px = random.randint(-15, max(0, img_size - bound_w + 15))
            py = random.randint(-15, max(0, img_size - bound_h + 15))

            # Compute intersection coordinates
            x1 = max(0, px)
            y1 = max(0, py)
            x2 = min(img_size, px + bound_w)
            y2 = min(img_size, py + bound_h)

            if x2 <= x1 or y2 <= y1:
                continue

            # Bulb sub-rect coordinates
            bx1 = x1 - px
            by1 = y1 - py
            bx2 = bx1 + (x2 - x1)
            by2 = by1 + (y2 - y1)

            bulb_crop = bulb_rgb[by1:by2, bx1:bx2]
            alpha_crop = a[by1:by2, bx1:bx2]

            # Full canvas mask for this instance
            inst_mask = np.zeros((img_size, img_size), dtype=np.uint8)
            inst_mask[y1:y2, x1:x2] = (alpha_crop > 120).astype(np.uint8) * 255

            if np.count_nonzero(inst_mask) < 400:
                continue

            # Render drop shadow under bulb
            shadow_off = random.randint(4, 8)
            sy1 = min(img_size, y1 + shadow_off)
            sy2 = min(img_size, y2 + shadow_off)
            sx1 = min(img_size, x1 + shadow_off)
            sx2 = min(img_size, x2 + shadow_off)
            sh_h = sy2 - sy1
            sh_w = sx2 - sx1
            if sh_h > 0 and sh_w > 0:
                s_mask = cv2.GaussianBlur(alpha_crop[:sh_h, :sh_w], (15, 15), 0)
                s_alpha = (s_mask.astype(np.float32) / 255.0) * 0.40
                canvas_sub = canvas[sy1:sy2, sx1:sx2].astype(np.float32)
                shadowed = canvas_sub * (1.0 - s_alpha[:, :, None]) + np.array([25, 25, 25]) * s_alpha[:, :, None]
                canvas[sy1:sy2, sx1:sx2] = shadowed.astype(np.uint8)

            # Alpha blend bulb onto canvas
            alpha_norm = (alpha_crop.astype(np.float32) / 255.0)[:, :, None]
            c_bg = canvas[y1:y2, x1:x2].astype(np.float32)
            c_fg = bulb_crop.astype(np.float32)
            blended = c_bg * (1.0 - alpha_norm) + c_fg * alpha_norm
            canvas[y1:y2, x1:x2] = blended.astype(np.uint8)

            placed_instances.append(inst_mask)

        # Now compute exact visible polygon for each instance
        # For instance i, visible pixels = inst_mask[i] & ~union(inst_mask[j] for j > i)
        labels_lines = []
        accumulated_occluder = np.zeros((img_size, img_size), dtype=bool)

        for i in reversed(range(len(placed_instances))):
            cur_mask = placed_instances[i] > 0
            visible_mask = cur_mask & ~accumulated_occluder
            accumulated_occluder |= cur_mask

            vis_uint8 = visible_mask.astype(np.uint8) * 255
            cnts, _ = cv2.findContours(vis_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not cnts:
                continue

            for c in cnts:
                area = cv2.contourArea(c)
                if area < 600:  # Skip tiny slivers
                    continue

                # Approximate polygon with ~20-30 points
                peri = cv2.arcLength(c, True)
                epsilon = max(1.0, 0.008 * peri)
                approx = cv2.approxPolyDP(c, epsilon, True)
                if len(approx) < 4:
                    continue

                # Flatten and normalize
                pts = approx.reshape(-1, 2)
                norm_pts = []
                for pt in pts:
                    norm_pts.extend([round(float(pt[0]) / img_size, 4), round(float(pt[1]) / img_size, 4)])

                line = "0 " + " ".join(str(p) for p in norm_pts)
                labels_lines.append(line)

        # Save image and label
        img_file = OUTPUT_DIR / "images" / split / f"{filename}.jpg"
        lbl_file = OUTPUT_DIR / "labels" / split / f"{filename}.txt"

        cv2.imwrite(str(img_file), canvas, [cv2.IMWRITE_JPEG_QUALITY, 93])
        with open(lbl_file, "w") as f:
            f.write("\n".join(labels_lines) + "\n")

        if (scene_idx + 1) % 20 == 0 or scene_idx == total_scenes - 1:
            print(f"Generated {scene_idx + 1} / {total_scenes} scenes...")

    # Write data.yaml
    yaml_content = f"""path: {OUTPUT_DIR.resolve().as_posix()}
train: images/train
val: images/val

names:
  0: onion
"""
    yaml_path = OUTPUT_DIR / "data.yaml"
    with open(yaml_path, "w") as f:
        f.write(yaml_content)

    print(f"Photorealistic dataset complete at {OUTPUT_DIR} with data.yaml")
    return yaml_path

if __name__ == "__main__":
    generate_dataset(num_train=80, num_val=20)
