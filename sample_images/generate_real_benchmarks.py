"""
Generates rich, high-realism benchmark images for forensic analysis testing.
Includes authentic camera photos with genuine EXIF as well as realistic tampering cases.
"""
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def create_sample_benchmarks(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    h, w = 600, 800

    # -------------------------------------------------------------
    # 1. AUTHENTIC DSLR LANDSCAPE
    # -------------------------------------------------------------
    img1 = np.zeros((h, w, 3), dtype=np.float32)
    # Sky gradient
    for y in range(h // 2):
        factor = y / (h / 2.0)
        img1[y, :] = [210 - factor * 40, 160 + factor * 20, 100 + factor * 50]  # RGB

    # Sun
    cv2.circle(img1, (620, 120), 45, (255, 245, 200), -1)

    # Mountain ridges (smooth continuous natural edges)
    for x in range(w):
        y_ridge = int(h * 0.45 + np.sin(x * 0.015) * 40 + np.cos(x * 0.005) * 20)
        img1[y_ridge : h // 2 + 50, x] = [70, 90, 110]

    # Forest / Meadow ground
    for y in range(h // 2, h):
        factor = (y - h // 2) / (h / 2.0)
        img1[y, :] = [30 + factor * 20, 110 - factor * 30, 40 + factor * 10]

    # Trees (natural repetitive textures with organic noise)
    for tx in range(50, w - 50, 60):
        ty = int(h * 0.65 + (tx % 30))
        cv2.circle(img1, (tx, ty), 35, (20, 85, 30), -1)
        cv2.rectangle(img1, (tx - 5, ty + 20), (tx + 5, ty + 60), (35, 25, 15), -1)

    # Realistic physical sensor noise (Shot noise + Read noise)
    shot_noise = np.random.normal(0, 3.5, (h, w, 3)).astype(np.float32)
    img1_noisy = np.clip(img1 + shot_noise, 0, 255).astype(np.uint8)

    pil_img1 = Image.fromarray(img1_noisy)
    exif1 = pil_img1.getexif()
    exif1[271] = "Canon"  # Make
    exif1[272] = "Canon EOS 5D Mark IV"  # Model
    exif1[306] = "2024:06:18 10:45:22"
    path1 = os.path.join(output_dir, "1_authentic_dslr_landscape.jpg")
    pil_img1.save(path1, format="JPEG", quality=93, exif=exif1)
    print(f"Generated: {path1}")

    # -------------------------------------------------------------
    # 2. AUTHENTIC IPHONE PORTRAIT WITH BOKEH
    # -------------------------------------------------------------
    img2 = np.zeros((h, w, 3), dtype=np.float32)
    # Soft out-of-focus background (bokeh)
    for y in range(h):
        for x in range(w):
            img2[y, x] = [140 + int(30 * np.sin(x*0.01)), 180 + int(20 * np.cos(y*0.01)), 210]
    img2_bg_blur = cv2.GaussianBlur(img2, (45, 45), 0)

    # Sharp portrait subject in foreground
    cx, cy = 400, 320
    # Head & shoulders
    cv2.ellipse(img2_bg_blur, (cx, cy), (120, 160), 0, 0, 360, (230, 185, 150), -1)
    cv2.circle(img2_bg_blur, (cx - 45, cy - 30), 12, (60, 40, 30), -1)  # Eyes
    cv2.circle(img2_bg_blur, (cx + 45, cy - 30), 12, (60, 40, 30), -1)
    cv2.ellipse(img2_bg_blur, (cx, cy + 45), (40, 20), 0, 0, 180, (190, 70, 70), -1)  # Smile
    # Hair
    cv2.ellipse(img2_bg_blur, (cx, cy - 90), (130, 90), 0, 180, 360, (40, 25, 20), -1)

    # Uniform smartphone noise floor
    phone_noise = np.random.normal(0, 2.8, (h, w, 3)).astype(np.float32)
    img2_noisy = np.clip(img2_bg_blur + phone_noise, 0, 255).astype(np.uint8)

    pil_img2 = Image.fromarray(img2_noisy)
    exif2 = pil_img2.getexif()
    exif2[271] = "Apple"
    exif2[272] = "iPhone 15 Pro"
    exif2[306] = "2024:08:10 16:30:15"
    path2 = os.path.join(output_dir, "2_authentic_iphone_portrait.jpg")
    pil_img2.save(path2, format="JPEG", quality=92, exif=exif2)
    print(f"Generated: {path2}")

    # -------------------------------------------------------------
    # 3. SPLICED COMPOSITE (Foreign spliced moon with noise mismatch)
    # -------------------------------------------------------------
    img3 = img1_noisy.copy().astype(np.float32)
    
    # Create foreign uncompressed object with distinct high noise & hard boundary
    moon_radius = 65
    my, mx = 180, 260
    moon_patch = np.zeros((moon_radius * 2, moon_radius * 2, 3), dtype=np.float32)
    cv2.circle(moon_patch, (moon_radius, moon_radius), moon_radius - 2, (245, 240, 220), -1)
    # Add lunar texture craters
    cv2.circle(moon_patch, (moon_radius - 20, moon_radius - 15), 14, (190, 185, 170), -1)
    cv2.circle(moon_patch, (moon_radius + 25, moon_radius + 10), 18, (180, 175, 160), -1)
    cv2.circle(moon_patch, (moon_radius - 10, moon_radius + 25), 10, (195, 190, 175), -1)
    
    # Severe foreign noise mismatch
    foreign_noise = np.random.normal(0, 14.0, (moon_radius * 2, moon_radius * 2, 3)).astype(np.float32)
    moon_patch = np.clip(moon_patch + foreign_noise, 0, 255)

    # Insert with harsh cut-out mask (splicing)
    mask = np.zeros((moon_radius * 2, moon_radius * 2), dtype=np.float32)
    cv2.circle(mask, (moon_radius, moon_radius), moon_radius - 2, 1.0, -1)
    
    for c in range(3):
        img3[my - moon_radius : my + moon_radius, mx - moon_radius : mx + moon_radius, c] = (
            img3[my - moon_radius : my + moon_radius, mx - moon_radius : mx + moon_radius, c] * (1.0 - mask) +
            moon_patch[:, :, c] * mask
        )

    pil_img3 = Image.fromarray(np.clip(img3, 0, 255).astype(np.uint8))
    path3 = os.path.join(output_dir, "3_spliced_foreign_object.jpg")
    pil_img3.save(path3, format="JPEG", quality=95)
    print(f"Generated: {path3}")

    # -------------------------------------------------------------
    # 4. COPY-MOVE CLONE FORGERY (Duplicated birds in sky)
    # -------------------------------------------------------------
    img4 = img1_noisy.copy()
    
    # Draw detailed textured bird pattern
    def draw_detailed_bird(arr, bx, by):
        cv2.ellipse(arr, (bx, by), (28, 12), -20, 0, 360, (25, 25, 30), -1)
        # Wings
        pts_w1 = np.array([[bx - 10, by], [bx - 35, by - 25], [bx - 15, by - 8]], np.int32)
        pts_w2 = np.array([[bx + 10, by], [bx + 35, by - 25], [bx + 15, by - 8]], np.int32)
        cv2.fillPoly(arr, [pts_w1, pts_w2], (20, 20, 25))
        # Beak & details
        cv2.circle(arr, (bx + 26, by - 6), 4, (220, 160, 40), -1)
        cv2.line(arr, (bx - 20, by - 12), (bx - 30, by - 20), (255, 255, 255), 1)

    # Original bird
    draw_detailed_bird(img4, 220, 140)
    # Cloned copy 1
    draw_detailed_bird(img4, 540, 140)
    # Cloned copy 2
    draw_detailed_bird(img4, 380, 230)

    pil_img4 = Image.fromarray(img4)
    path4 = os.path.join(output_dir, "4_copy_move_cloned_birds.png")
    pil_img4.save(path4, format="PNG")
    print(f"Generated: {path4}")

    # -------------------------------------------------------------
    # 5. RETOUCHED PHOTOSHOP EDITED PORTRAIT
    # -------------------------------------------------------------
    img5 = img2_noisy.copy()
    # Inpainted / healed skin (wiping out noise floor locally)
    smoothed_skin = cv2.bilateralFilter(img5[280:360, 360:440], 25, 120, 120)
    img5[280:360, 360:440] = smoothed_skin

    pil_img5 = Image.fromarray(img5)
    exif5 = pil_img5.getexif()
    exif5[305] = "Adobe Photoshop 2024 (Windows)"
    exif5[306] = "2024:08:12 21:15:00"
    path5 = os.path.join(output_dir, "5_retouched_photoshop_portrait.jpg")
    pil_img5.save(path5, format="JPEG", quality=90, exif=exif5)
    print(f"Generated: {path5}")

    return [path1, path2, path3, path4, path5]


if __name__ == "__main__":
    create_sample_benchmarks(os.path.join(os.path.dirname(__file__), "benchmarks"))
