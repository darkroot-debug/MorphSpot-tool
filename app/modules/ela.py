"""
Error Level Analysis (ELA) Forensic Detection Module.

Error Level Analysis operates by intentionally recompressing an image at a known
JPEG quality and measuring the localized discrepancy between the original and
recompressed pixel arrays. Because genuine JPEG images reach an error equilibrium,
spliced or modified areas stand out with disproportionate error rates.
"""
import io
from typing import Any, Dict, Tuple
import cv2
import numpy as np
from PIL import Image

from app.config import ELAConfig, DEFAULT_CONFIG
from app.utils.visualizer import create_heatmap, normalize_to_uint8


class ELADetector:
    """Detects compression inconsistencies and localized editing using Error Level Analysis."""

    def __init__(self, config: ELAConfig = DEFAULT_CONFIG.ela):
        self.config = config

    def analyze(self, image_rgb: np.ndarray) -> Dict[str, Any]:
        """
        Executes Error Level Analysis on an RGB image array.

        Returns:
            Dict containing:
                score_percentage (float): Tampering likelihood score (0 to 100%)
                details (str): Human-readable forensic interpretation
                metrics (dict): Quantitative metrics (mean_diff, max_diff, variance_disparity, etc.)
                difference_map (np.ndarray): 2D grayscale discrepancy map (uint8)
                heatmap_rgb (np.ndarray): 3D RGB pseudo-color heatmap (uint8)
        """
        h, w, c = image_rgb.shape
        pil_img = Image.fromarray(image_rgb)

        # 1. Recompress to in-memory JPEG buffer
        buffer = io.BytesIO()
        pil_img.save(buffer, format="JPEG", quality=self.config.quality)
        buffer.seek(0)
        recompressed_pil = Image.open(buffer)
        recompressed_rgb = np.array(recompressed_pil, dtype=np.float32)
        original_float = image_rgb.astype(np.float32)

        # 2. Compute absolute difference
        diff = np.abs(original_float - recompressed_rgb)
        diff_max_channel = np.max(diff, axis=2)  # Peak channel difference per pixel

        # 3. Enhanced difference map for visualization
        scaled_diff = diff_max_channel * self.config.scale_multiplier
        scaled_diff_uint8 = np.clip(scaled_diff, 0, 255).astype(np.uint8)

        # 4. Patch-based statistical variance analysis
        p_size = self.config.patch_size
        num_patches_y = max(1, h // p_size)
        num_patches_x = max(1, w // p_size)

        patch_means = []
        patch_stds = []

        for y in range(0, h - p_size + 1, p_size):
            for x in range(0, w - p_size + 1, p_size):
                patch = diff_max_channel[y : y + p_size, x : x + p_size]
                patch_means.append(np.mean(patch))
                patch_stds.append(np.std(patch))

        patch_means = np.array(patch_means)
        patch_stds = np.array(patch_stds)

        global_mean = float(np.mean(diff_max_channel))
        global_std = float(np.std(diff_max_channel))
        global_max = float(np.max(diff_max_channel))

        # Variance of patch statistics indicates localized anomaly
        if len(patch_stds) > 1:
            mean_patch_std = float(np.mean(patch_stds))
            std_patch_std = float(np.std(patch_stds))
            # Ratio of high-variance patches
            high_error_threshold = global_mean + 1.8 * global_std
            anomalous_patches = np.sum(patch_means > high_error_threshold)
            anomaly_ratio = float(anomalous_patches / len(patch_means))
            disparity_cv = (std_patch_std / (mean_patch_std + 1e-6))  # Coefficient of variation
        else:
            disparity_cv = 0.0
            anomaly_ratio = 0.0
            std_patch_std = 0.0

        # 5. Compute Tampering Probability Score (0 to 100%)
        # Natural scenes have mild baseline texture variations (CV ~0.3 - 0.5).
        # Spliced regions produce severe, localized spikes (CV > 0.8, anomaly ratio > 0.08).
        score = 0.0

        # Disparity component with natural texture deadband (ignore CV below 0.35)
        effective_cv = max(0.0, disparity_cv - 0.35)
        score += min(50.0, (effective_cv / 0.85) * 50.0)

        # Anomaly patch ratio component with baseline tolerance (ignore ratio below 0.04)
        effective_ratio = max(0.0, anomaly_ratio - 0.04)
        score += min(35.0, (effective_ratio / 0.12) * 35.0)

        # Extreme peak error component
        if global_max > 38.0:
            score += min(15.0, ((global_max - 38.0) / 35.0) * 15.0)

        # Baseline noise adjustment: if image has nearly zero difference everywhere, it's pristine re-saved JPEG
        if global_mean < 0.8 and disparity_cv < 0.4:
            score = max(0.0, score * 0.4)

        score_percentage = float(np.clip(round(score, 1), 0.0, 100.0))

        # 6. Generate Forensic Details Description
        if score_percentage > 70.0:
            details = (
                f"Severe Error Level disparity detected (Disparity CV: {disparity_cv:.2f}, "
                f"Peak Error: {global_max:.1f}). High-frequency compression artifact mismatches "
                f"strongly indicate composite splicing or localized manipulation."
            )
        elif score_percentage > 35.0:
            details = (
                f"Moderate compression artifact variance observed (Disparity CV: {disparity_cv:.2f}). "
                f"Localized error fluctuations suggest potential selective editing or re-saving."
            )
        else:
            details = (
                f"Uniform error level distribution across image grid (Mean: {global_mean:.2f}, "
                f"Disparity CV: {disparity_cv:.2f}). No significant compression boundaries detected."
            )

        # 7. Generate Heatmap
        heatmap_rgb = create_heatmap(scaled_diff_uint8, cv2.COLORMAP_JET)

        return {
            "score_percentage": score_percentage,
            "details": details,
            "metrics": {
                "global_mean_error": round(global_mean, 3),
                "global_std_error": round(global_std, 3),
                "peak_error": round(global_max, 2),
                "disparity_cv": round(disparity_cv, 3),
                "anomalous_patch_ratio": round(anomaly_ratio, 4),
            },
            "difference_map": scaled_diff_uint8,
            "heatmap_rgb": heatmap_rgb,
        }
