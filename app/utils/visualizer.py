"""
Visualization utility functions for forensic heatmaps, overlays, and annotations.
"""
import base64
import io
from typing import List, Optional, Tuple
import cv2
import numpy as np
from PIL import Image


def normalize_to_uint8(data: np.ndarray, clip_percentiles: Tuple[float, float] = (1.0, 99.0)) -> np.ndarray:
    """
    Normalizes a floating-point or integer array to 0-255 uint8 range
    using percentile clipping for enhanced dynamic range.
    """
    if data.size == 0:
        return np.zeros((1, 1), dtype=np.uint8)
    
    p_low, p_high = np.percentile(data, clip_percentiles)
    if p_high > p_low:
        clipped = np.clip(data, p_low, p_high)
        norm = ((clipped - p_low) / (p_high - p_low) * 255.0).astype(np.uint8)
    else:
        norm = np.zeros_like(data, dtype=np.uint8)
    return norm


def create_heatmap(
    intensity_map: np.ndarray,
    colormap: int = cv2.COLORMAP_JET
) -> np.ndarray:
    """
    Converts a 2D intensity map (0-255 or float) to an RGB pseudo-color heatmap.
    """
    if intensity_map.dtype != np.uint8:
        intensity_map = normalize_to_uint8(intensity_map)
    
    heatmap_bgr = cv2.applyColorMap(intensity_map, colormap)
    heatmap_rgb = cv2.cvtColor(heatmap_bgr, cv2.COLOR_BGR2RGB)
    return heatmap_rgb


def create_blended_overlay(
    original_rgb: np.ndarray,
    heatmap_rgb: np.ndarray,
    alpha: float = 0.55
) -> np.ndarray:
    """
    Blends an original image with a forensic heatmap.
    """
    if original_rgb.shape[:2] != heatmap_rgb.shape[:2]:
        heatmap_rgb = cv2.resize(
            heatmap_rgb,
            (original_rgb.shape[1], original_rgb.shape[0]),
            interpolation=cv2.INTER_LINEAR
        )
    
    blended = cv2.addWeighted(original_rgb, 1.0 - alpha, heatmap_rgb, alpha, 0)
    return blended


def draw_copy_move_annotations(
    image_rgb: np.ndarray,
    matches: List[Tuple[Tuple[float, float], Tuple[float, float]]],
    clusters: Optional[List[List[Tuple[float, float]]]] = None
) -> np.ndarray:
    """
    Draws copy-move connection vectors and cluster indicators on an image.
    """
    annotated = image_rgb.copy()
    colors = [
        (255, 60, 60), (60, 255, 60), (60, 120, 255),
        (255, 200, 40), (255, 60, 255), (40, 255, 255)
    ]
    
    # Draw match lines
    for i, (pt1, pt2) in enumerate(matches):
        p1 = (int(round(pt1[0])), int(round(pt1[1])))
        p2 = (int(round(pt2[0])), int(round(pt2[1])))
        color = colors[i % len(colors)]
        
        # Arrow line showing duplication trajectory
        cv2.arrowedLine(annotated, p1, p2, color, thickness=2, tipLength=0.15)
        cv2.circle(annotated, p1, radius=4, color=(255, 255, 255), thickness=-1)
        cv2.circle(annotated, p1, radius=4, color=color, thickness=1)
        cv2.circle(annotated, p2, radius=4, color=(255, 255, 255), thickness=-1)
        cv2.circle(annotated, p2, radius=4, color=color, thickness=1)

    # Draw convex hulls around cluster points if present
    if clusters:
        for idx, cluster in enumerate(clusters):
            if len(cluster) >= 3:
                pts = np.array([[int(p[0]), int(p[1])] for p in cluster], dtype=np.int32)
                hull = cv2.convexHull(pts)
                color = colors[idx % len(colors)]
                cv2.drawContours(annotated, [hull], 0, color, thickness=2)
                
                # Draw semi-transparent fill
                overlay = annotated.copy()
                cv2.drawContours(overlay, [hull], 0, color, thickness=-1)
                cv2.addWeighted(overlay, 0.25, annotated, 0.75, 0, annotated)

    return annotated


def encode_image_to_base64(img_rgb: np.ndarray, format: str = "JPEG", quality: int = 85) -> str:
    """Encodes an RGB numpy array to a base64 data string."""
    if img_rgb.dtype != np.uint8:
        img_rgb = np.clip(img_rgb, 0, 255).astype(np.uint8)
    
    pil_img = Image.fromarray(img_rgb)
    buf = io.BytesIO()
    if format.upper() in ("JPEG", "JPG"):
        pil_img.save(buf, format="JPEG", quality=quality)
        mime = "image/jpeg"
    else:
        pil_img.save(buf, format="PNG")
        mime = "image/png"
    
    b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:{mime};base64,{b64_data}"
