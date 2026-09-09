"""
Edge Inconsistency and Blending Artifacts Detection Module.

Identifies boundary anomalies created during image splicing and composition,
such as unnatural sharpness disparities, Gaussian feathering halos, and
discontinuous blur transitions along object contours.
"""
from typing import Any, Dict, List
import cv2
import numpy as np

from app.config import EdgeConfig, DEFAULT_CONFIG
from app.utils.visualizer import create_heatmap, normalize_to_uint8


class EdgeInconsistencyDetector:
    """Analyzes gradient profiles and contour sharpness consistency to detect splicing boundaries."""

    def __init__(self, config: EdgeConfig = DEFAULT_CONFIG.edges):
        self.config = config

    def analyze(self, image_rgb: np.ndarray) -> Dict[str, Any]:
        """
        Executes edge sharpness and blending boundary analysis.

        Returns:
            Dict containing:
                score_percentage (float): Tampering likelihood score (0 to 100%)
                details (str): Forensic interpretation
                metrics (dict): Mean edge width, sharpness disparity, anomalous contour count
                edge_mask (np.ndarray): Binary edge mask (uint8)
                heatmap_rgb (np.ndarray): Edge anomaly heatmap (RGB uint8)
        """
        h, w, _ = image_rgb.shape
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
        gray_float = gray.astype(np.float32)

        # 1. Compute Sobel Gradients
        sobel_x = cv2.Sobel(gray_float, cv2.CV_32F, 1, 0, ksize=self.config.sobel_kernel_size)
        sobel_y = cv2.Sobel(gray_float, cv2.CV_32F, 0, 1, ksize=self.config.sobel_kernel_size)
        grad_mag = np.sqrt(sobel_x**2 + sobel_y**2)
        grad_orient = np.arctan2(sobel_y, sobel_x)

        # 2. Canny Edge Detection
        canny_edges = cv2.Canny(gray, self.config.canny_low, self.config.canny_high)

        # 3. Find Contours
        contours, _ = cv2.findContours(canny_edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

        edge_sharpness_list: List[float] = []
        anomaly_edge_map = np.zeros((h, w), dtype=np.float32)

        # Sample points along contours to measure perpendicular gradient profiles
        for contour in contours:
            if len(contour) < 15:
                continue

            contour_sharpness = []
            for pt in contour[::3]:  # Subsample points along contour
                x, y = pt[0]
                if 5 <= x < w - 5 and 5 <= y < h - 5:
                    angle = grad_orient[y, x]
                    # Sample normal line across edge (5 pixels in both directions)
                    dx = np.cos(angle)
                    dy = np.sin(angle)

                    profile = []
                    for t in range(-4, 5):
                        px = int(round(x + t * dx))
                        py = int(round(y + t * dy))
                        if 0 <= px < w and 0 <= py < h:
                            profile.append(grad_mag[py, px])

                    if len(profile) == 9:
                        peak_val = max(profile)
                        min_val = min(profile)
                        contrast = peak_val - min_val
                        # Sharpness estimation
                        sharpness = contrast / (np.std(profile) + 1e-4)
                        contour_sharpness.append((x, y, sharpness))
                        edge_sharpness_list.append(sharpness)

        if len(edge_sharpness_list) > 10:
            edge_arr = np.array(edge_sharpness_list, dtype=np.float32)
            med_sharpness = float(np.median(edge_arr))
            sharpness_std = float(np.std(edge_arr))
            sharpness_iqr = float(np.percentile(edge_arr, 75) - np.percentile(edge_arr, 25))
            sharpness_cv = sharpness_std / (med_sharpness + 1e-5)

            # Mark anomalous contour points (extremely sharp cut-outs or over-blurred seams)
            upper_bound = np.percentile(edge_arr, 95)
            lower_bound = np.percentile(edge_arr, 5)

            for contour in contours:
                if len(contour) < 15:
                    continue
                for pt in contour:
                    x, y = pt[0]
                    if 0 <= x < w and 0 <= y < h:
                        local_mag = grad_mag[y, x]
                        if local_mag > 30:
                            # Distance from median profile
                            dev = abs(local_mag - med_sharpness) / (sharpness_std + 1e-4)
                            anomaly_edge_map[y, x] = dev

            # Dilate anomaly map for continuous visual heatmap
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            dilated_anomaly = cv2.dilate(anomaly_edge_map, kernel)
            dilated_anomaly = cv2.GaussianBlur(dilated_anomaly, (15, 15), 0)

            # High anomaly pixel count
            anomalous_edges_ratio = float(np.sum(dilated_anomaly > 2.0) / max(1, np.sum(canny_edges > 0)))
        else:
            med_sharpness = 0.0
            sharpness_std = 0.0
            sharpness_cv = 0.0
            anomalous_edges_ratio = 0.0
            dilated_anomaly = np.zeros((h, w), dtype=np.float32)

        # 4. Tampering Probability Score (0 to 100%)
        # Natural optical depth of field (DoF) produces soft background bokeh (CV ~0.3 - 0.6).
        # Tampered cut-outs and alpha blending produce sharp step spikes (CV > 0.9, anomaly ratio > 0.10).
        score = 0.0

        # Disparity in edge profile distribution with optical DoF deadband (ignore CV below 0.40)
        effective_sharpness_cv = max(0.0, sharpness_cv - 0.40)
        score += min(45.0, (effective_sharpness_cv / 1.1) * 45.0)

        # Anomalous edge ratio with baseline tolerance (ignore ratio below 0.05)
        effective_edge_ratio = max(0.0, anomalous_edges_ratio - 0.05)
        score += min(45.0, (effective_edge_ratio / 0.15) * 45.0)

        # Extreme sharpness disparity
        if sharpness_std > 30.0:
            score += min(10.0, ((sharpness_std - 30.0) / 25.0) * 10.0)

        score_percentage = float(np.clip(round(score, 1), 0.0, 100.0))

        # 5. Descriptive Details
        if score_percentage > 70.0:
            details = (
                f"Severe edge sharpness disparity detected (Sharpness CV: {sharpness_cv:.2f}, "
                f"Anomaly Ratio: {anomalous_edges_ratio*100:.1f}%). Unnatural gradient transitions "
                f"and sharp boundary cut-outs strongly indicate composite splicing or alpha matting."
            )
        elif score_percentage > 35.0:
            details = (
                f"Moderate edge contour inconsistency observed (Sharpness CV: {sharpness_cv:.2f}). "
                f"Minor boundary transition anomalies along object contours."
            )
        else:
            details = (
                f"Natural and homogeneous edge gradient profiles across image structures "
                f"(Median Sharpness: {med_sharpness:.2f}, CV: {sharpness_cv:.2f}). No splice boundaries found."
            )

        # 6. Generate Heatmap
        norm_anomaly = normalize_to_uint8(dilated_anomaly)
        heatmap_rgb = create_heatmap(norm_anomaly, cv2.COLORMAP_MAGMA)

        return {
            "score_percentage": score_percentage,
            "details": details,
            "metrics": {
                "median_sharpness": round(med_sharpness, 2),
                "sharpness_std": round(sharpness_std, 2),
                "sharpness_cv": round(sharpness_cv, 3),
                "anomalous_edges_ratio": round(anomalous_edges_ratio, 4),
            },
            "edge_mask": canny_edges,
            "heatmap_rgb": heatmap_rgb,
        }
