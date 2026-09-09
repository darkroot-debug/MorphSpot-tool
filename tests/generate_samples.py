"""
Generates synthetic forensic test fixtures for unit and integration testing.
"""
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def generate_fixtures(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    # 1. Authentic Image: Coherent lighting, uniform noise, uniform JPEG compression
    h, w = 400, 600
    authentic_img = np.zeros((h, w, 3), dtype=np.uint8)

    # Gradient background
    for y in range(h):
        for x in range(w):
            r = int(50 + 150 * (y / h))
            g = int(80 + 100 * (x / w))
            b = int(180 - 80 * (y / h))
            authentic_img[y, x] = [r, g, b]

    # Draw soft circle
    cv2.circle(authentic_img, (300, 200), 60, (240, 220, 100), -1)

    # Add realistic sensor noise
    noise = np.random.normal(0, 4.0, (h, w, 3)).astype(np.float32)
    authentic_noisy = np.clip(authentic_img.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    authentic_pil = Image.fromarray(authentic_noisy)
    authentic_path = os.path.join(output_dir, "authentic_sample.jpg")
    authentic_pil.save(authentic_path, format="JPEG", quality=90)
    print(f"Generated: {authentic_path}")

    # 2. Copy-Move Forgery: Distinct textured pattern duplicated at distant location
    cm_img = authentic_noisy.copy()

    # Create rich patterned stamp
    def draw_stamp(target_arr, cx, cy):
        cv2.rectangle(target_arr, (cx - 45, cy - 45), (cx + 45, cy + 45), (30, 210, 255), -1)
        cv2.rectangle(target_arr, (cx - 35, cy - 35), (cx + 35, cy + 35), (20, 20, 20), -1)
        cv2.circle(target_arr, (cx, cy), 22, (255, 60, 120), -1)
        cv2.circle(target_arr, (cx, cy), 12, (255, 255, 255), -1)
        cv2.circle(target_arr, (cx, cy), 5, (0, 0, 0), -1)
        cv2.putText(target_arr, "MORPH", (cx - 32, cy + 32), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
        for angle in range(0, 360, 45):
            rad = np.deg2rad(angle)
            p1 = (int(cx + 14 * np.cos(rad)), int(cy + 14 * np.sin(rad)))
            p2 = (int(cx + 30 * np.cos(rad)), int(cy + 30 * np.sin(rad)))
            cv2.line(target_arr, p1, p2, (255, 255, 0), 1)

    draw_stamp(cm_img, 130, 180)  # Original stamp
    draw_stamp(cm_img, 470, 180)  # Cloned duplicate!

    cm_pil = Image.fromarray(cm_img)
    cm_path = os.path.join(output_dir, "copy_move_sample.jpg")
    cm_pil.save(cm_path, format="PNG")  # Use PNG for fixture to retain exact keypoints
    print(f"Generated: {cm_path}")

    # 3. Spliced Composite Image: High-noise patch spliced onto low-noise background with sharp edge
    spliced_img = authentic_noisy.copy()
    
    # Generate foreign patch with extreme noise & color
    splice_h, splice_w = 120, 140
    sy, sx = 140, 230
    foreign_patch = np.zeros((splice_h, splice_w, 3), dtype=np.uint8)
    foreign_patch[:, :] = [220, 50, 50]
    # Heavy foreign noise
    foreign_noise = np.random.normal(0, 18.0, (splice_h, splice_w, 3)).astype(np.float32)
    foreign_patch = np.clip(foreign_patch.astype(np.float32) + foreign_noise, 0, 255).astype(np.uint8)
    cv2.putText(foreign_patch, "SPLICED", (15, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    # Insert into host image with zero blending (harsh boundary)
    spliced_img[sy : sy + splice_h, sx : sx + splice_w] = foreign_patch

    spliced_pil = Image.fromarray(spliced_img)
    spliced_path = os.path.join(output_dir, "spliced_sample.jpg")
    spliced_pil.save(spliced_path, format="JPEG", quality=95)
    print(f"Generated: {spliced_path}")

    # 4. Metadata Tampered Image: Contains Photoshop signature
    meta_img = authentic_pil.copy()
    exif = meta_img.getexif()
    # Tag 305 is 'Software'
    exif[305] = "Adobe Photoshop CC 2024 (Windows)"
    exif[306] = "2026:08:15 22:30:00"  # DateTime
    meta_path = os.path.join(output_dir, "metadata_tampered_sample.jpg")
    meta_img.save(meta_path, format="JPEG", quality=90, exif=exif)
    print(f"Generated: {meta_path}")

    return {
        "authentic": authentic_path,
        "copy_move": cm_path,
        "spliced": spliced_path,
        "metadata_tampered": meta_path,
    }


if __name__ == "__main__":
    generate_fixtures(os.path.join(os.path.dirname(__file__), "sample_fixtures"))
