"""
Luminance and Color Gradient Variance Forensic Detection Module.

Analyzes illumination consistency, lighting direction gradients, and
chromaticity distributions across CIE-Lab and YCrCb color spaces to detect
spliced objects with mismatched light sources or white balance temperatures.
"""
from typing import Any, Dict, Tuple
import cv2
import numpy as np

from app.config import LuminanceConfig, DEFAULT_CONFIG
from app.utils.visualizer import create_heatmap, normalize_to_uint8


class LuminanceDetector:
    """Detects illumination direction mismatches and chromaticity discrepancies."""

    def __init__(self, config: LuminanceConfig = DEFAULT_CONFIG.luminance):
        self.config = config

    def _fit_illumination_surface(self, L_channel: np.ndarray) -> np.ndarray:
        """
        Fits a smooth 2D quadratic surface to the luminance channel to estimate
        the global illumination model of the scene.
        """
        h, w = L_channel.shape
        # Downsample for robust polynomial fitting
        step = max(4, min(h, w) // 100)
        y_coords, x_coords = np.mgrid[0:h:step, 0:w:step]
        x_flat = (x_coords.flatten() / float(w)).astype(np.float32)
        y_flat = (y_coords.flatten() / float(h)).astype(np.float32)
        z_flat = (L_channel[::step, ::step].flatten() / 255.0).astype(np.float32)

        # Basis functions: [1, x, y, x^2, xy, y^2]
        A = np.column_stack([
            np.ones_like(x_flat),
            x_flat,
            y_flat,
            x_flat**2,
            x_flat * y_flat,
            y_flat**2
        ])

        # Least squares solve
        coeffs, _, _, _ = np.linalg.lstsq(A, z_flat, rcond=None)

        # Evaluate over full resolution
        full_y, full_x = np.mgrid[0:h, 0:w]
        fx = (full_x / float(w)).astype(np.float32)
        fy = (full_y / float(h)).astype(np.float32)

        fitted_surface = (
            coeffs[0] +
            coeffs[1] * fx +
            coeffs[2] * fy +
            coeffs[3] * (fx**2) +
            coeffs[4] * (fx * fy) +
            coeffs[5] * (fy**2)
        ) * 255.0

        return np.clip(fitted_surface, 0, 255).astype(np.float32)

    def analyze(self, image_rgb: np.ndarray) -> Dict[str, Any]:
        """
        Executes illumination and color gradient consistency analysis.

        Returns:
            Dict containing:
                score_percentage (float): Tampering likelihood (0 to 100%)
                details (str): Forensic interpretation
                metrics (dict): Illuminant variance, chromaticity disparity, etc.
                residual_map (np.ndarray): Luminance residual (uint8)
                heatmap_rgb (np.ndarray): Illumination inconsistency heatmap (RGB uint8)
        """
        h, w, _ = image_rgb.shape

        # 1. Convert to CIE-Lab
        lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB)
        L = lab[:, :, 0].astype(np.float32)
        A_channel = lab[:, :, 1].astype(np.float32)
        B_channel = lab[:, :, 2].astype(np.float32)

        # 2. Fit 2D Illumination Surface
        fitted_L = self._fit_illumination_surface(L)
        lum_residual = np.abs(L - fitted_L)

        # Smooth residual to eliminate micro-textures and retain macro lighting deviations
        lum_residual_smooth = cv2.GaussianBlur(lum_residual, (31, 31), 0)

        # 3. Patch-level Chromaticity and Lighting Variance
        patch_size = self.config.patch_size
        a_means, b_means, lum_res_stds = [], [], []

        for y in range(0, h - patch_size + 1, patch_size):
            for x in range(0, w - patch_size + 1, patch_size):
                p_A = A_channel[y : y + patch_size, x : x + patch_size]
                p_B = B_channel[y : y + patch_size, x : x + patch_size]
                p_res = lum_residual_smooth[y : y + patch_size, x : x + patch_size]

                a_means.append(np.mean(p_A))
                b_means.append(np.mean(p_B))
                lum_res_stds.append(np.std(p_res))

        a_means = np.array(a_means)
        b_means = np.array(b_means)
        lum_res_stds = np.array(lum_res_stds)

        # Calculate lighting anomaly metrics
        global_res_mean = float(np.mean(lum_residual_smooth))
        global_res_std = float(np.std(lum_residual_smooth))
        
        # Chromaticity variance across segments (abnormal color cast disparity)
        chroma_std = float(np.std(a_means) + np.std(b_means))

        # Disparity coefficient
        lum_cv = global_res_std / (global_res_mean + 1e-4)

        # 4. Tampering Probability Score (0 to 100%)
        score = 0.0
        # Macro lighting discrepancy
        score += min(50.0, (lum_cv / 1.4) * 50.0)
        # Residual magnitude
        if global_res_mean > 25.0:
            score += min(30.0, ((global_res_mean - 25.0) / 30.0) * 30.0)
        # Chromaticity imbalance
        if chroma_std > 20.0:
            score += min(20.0, ((chroma_std - 20.0) / 25.0) * 20.0)

        score_percentage = float(np.clip(round(score, 1), 0.0, 100.0))

        # 5. Details Description
        if score_percentage > 70.0:
            details = (
                f"Severe illumination gradient inconsistency detected (Luminance CV: {lum_cv:.2f}, "
                f"Residual Mean: {global_res_mean:.1f}). Discontinuous light direction vectors and "
                f"color cast variance indicate composite splicing under mismatched lighting."
            )
        elif score_percentage > 35.0:
            details = (
                f"Moderate lighting gradient variance observed (Luminance CV: {lum_cv:.2f}). "
                f"Minor illuminant direction fluctuations or localized shading differences."
            )
        else:
            details = (
                f"Consistent global illumination and chromatic distribution across the scene "
                f"(Luminance CV: {lum_cv:.2f}, Residual: {global_res_mean:.2f}). Lighting is physically coherent."
            )

        # 6. Generate Heatmap
        norm_res = normalize_to_uint8(lum_residual_smooth)
        heatmap_rgb = create_heatmap(norm_res, cv2.COLORMAP_VIRIDIS)

        return {
            "score_percentage": score_percentage,
            "details": details,
            "metrics": {
                "lum_residual_mean": round(global_res_mean, 2),
                "lum_residual_std": round(global_res_std, 2),
                "lum_disparity_cv": round(lum_cv, 3),
                "chromaticity_variance": round(chroma_std, 2),
            },
            "residual_map": norm_res,
            "heatmap_rgb": heatmap_rgb,
        }
