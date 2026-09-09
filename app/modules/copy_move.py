"""
Copy-Move / Clone Forgery Detection Module.

Identifies duplicated regions within an image using invariant feature detectors
(SIFT, ORB, AKAZE), k-NN descriptor matching, spatial distance thresholding,
and displacement vector clustering to distinguish genuine clone operations
from repetitive natural textures.
"""
from typing import Any, Dict, List, Tuple
import cv2
import numpy as np

from app.config import CopyMoveConfig, DEFAULT_CONFIG
from app.utils.visualizer import draw_copy_move_annotations, create_heatmap


class CopyMoveDetector:
    """Detects duplicated / cloned image regions with keypoint matching and spatial clustering."""

    def __init__(self, config: CopyMoveConfig = DEFAULT_CONFIG.copy_move):
        self.config = config

    def _get_detector_and_matcher(self):
        """Initializes detector (SIFT preferred, ORB/AKAZE fallback) and corresponding matcher."""
        try:
            detector = cv2.SIFT_create(nfeatures=self.config.max_features)
            # FLANN matcher for floating-point SIFT descriptors
            index_params = dict(algorithm=1, trees=5)  # FLANN_INDEX_KDTREE
            search_params = dict(checks=50)
            matcher = cv2.FlannBasedMatcher(index_params, search_params)
            norm_type = cv2.NORM_L2
            is_sift = True
        except Exception:
            # Fallback to ORB
            detector = cv2.ORB_create(nfeatures=self.config.max_features)
            matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            norm_type = cv2.NORM_HAMMING
            is_sift = False

        return detector, matcher, is_sift

    def _cluster_matches(
        self,
        valid_matches: List[Tuple[Tuple[float, float], Tuple[float, float]]],
        h: int,
        w: int
    ) -> Tuple[List[List[Tuple[float, float]]], int, float, bool]:
        """
        Clusters match vectors by displacement consistency (dx, dy), verifies 2D RANSAC
        geometric consistency, and filters out 1D periodic background textures (e.g. wall slats, fences).
        
        Returns:
            clusters: List of verified 2D clone clusters
            max_cluster_size: Count of RANSAC verified inliers
            consistency_score: 0.0 - 1.0 rating of displacement alignment
            is_periodic_texture: True if matches represent 1D repeating architectural textures
        """
        if len(valid_matches) < self.config.min_cluster_size:
            return [], 0, 0.0, False

        # Calculate displacement vectors: (dx, dy, length, angle)
        displacements = []
        for p1, p2 in valid_matches:
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            length = np.sqrt(dx**2 + dy**2)
            angle = np.arctan2(dy, dx) * 180 / np.pi
            displacements.append((dx, dy, length, angle))

        displacements = np.array(displacements)

        # Displacement binning
        bin_size = self.config.displacement_bin_size
        dx_bins = np.round(displacements[:, 0] / bin_size)
        dy_bins = np.round(displacements[:, 1] / bin_size)
        bins = [f"{int(x)}_{int(y)}" for x, y in zip(dx_bins, dy_bins)]

        from collections import Counter
        bin_counts = Counter(bins)

        # Detect Harmonic 1D periodic background texture (e.g. repeating slats at dx, 2*dx, 3*dx)
        # Check if multiple displacement clusters share collinear angles and integer multiple lengths
        is_harmonic_periodic = False
        dominant_bins = [k for k, count in bin_counts.items() if count >= 3]
        if len(dominant_bins) >= 2:
            disp_lengths = []
            disp_angles = []
            for k in dominant_bins:
                kx, ky = map(float, k.split('_'))
                dx_real = kx * bin_size
                dy_real = ky * bin_size
                disp_lengths.append(np.hypot(dx_real, dy_real))
                disp_angles.append(np.arctan2(dy_real, dx_real) * 180 / np.pi)
            
            # Check angle alignment (collinear within 5 degrees or 180 degrees)
            angle_diffs = [abs(disp_angles[i] - disp_angles[0]) % 180 for i in range(len(disp_angles))]
            if all(d < 6.0 or d > 174.0 for d in angle_diffs):
                # Check if lengths are approximate integer ratios (e.g. 156, 312, 468)
                min_len = min(disp_lengths)
                if min_len > 25.0:
                    ratios = [l / min_len for l in disp_lengths]
                    is_integer_multiple = all(abs(r - round(r)) < 0.20 for r in ratios)
                    if is_integer_multiple:
                        is_harmonic_periodic = True

        # Harmonic periodic texture: multiple bins at integer multiple steps
        dx_vals = np.abs(displacements[:, 0])
        dy_vals = np.abs(displacements[:, 1])

        verified_clusters = []
        max_inlier_count = 0

        for bin_key, count in bin_counts.items():
            if count >= self.config.min_cluster_size and not is_harmonic_periodic:
                cluster_matches = [valid_matches[idx] for idx, b in enumerate(bins) if b == bin_key]
                src_pts = np.array([m[0] for m in cluster_matches], dtype=np.float32)
                dst_pts = np.array([m[1] for m in cluster_matches], dtype=np.float32)

                src_min_x, src_max_x = src_pts[:, 0].min(), src_pts[:, 0].max()
                src_min_y, src_max_y = src_pts[:, 1].min(), src_pts[:, 1].max()
                dst_min_x, dst_max_x = dst_pts[:, 0].min(), dst_pts[:, 0].max()
                dst_min_y, dst_max_y = dst_pts[:, 1].min(), dst_pts[:, 1].max()

                src_w, src_h = max(1.0, src_max_x - src_min_x), max(1.0, src_max_y - src_min_y)
                dst_w, dst_h = max(1.0, dst_max_x - dst_min_x), max(1.0, dst_max_y - dst_min_y)

                # Check aspect ratio (thin elongated strips are wallpaper/stripes/slats, not 2D objects)
                aspect_ratio = max(src_w / max(src_h, 1.0), src_h / max(src_w, 1.0))
                is_elongated_strip = (aspect_ratio > 3.0 and min(src_w, src_h) < 55.0)

                # Check if cluster is an isolated compact 2D object
                is_compact_patch = (src_w < 0.38 * w and dst_w < 0.38 * w and src_h > 45.0) or (src_h < 0.38 * h and dst_h < 0.38 * h and src_w > 45.0)
                
                # Check overlap between source and destination spans (slatted walls overlap, cloned objects are disjoint)
                overlap_x = max(0.0, min(src_max_x, dst_max_x) - max(src_min_x, dst_min_x))
                overlap_y = max(0.0, min(src_max_y, dst_max_y) - max(src_min_y, dst_min_y))
                is_disjoint = (overlap_x < 0.15 * max(src_w, dst_w)) or (overlap_y < 0.15 * max(src_h, dst_h))

                src_std_x, src_std_y = np.std(src_pts[:, 0]), np.std(src_pts[:, 1])
                dst_std_x, dst_std_y = np.std(dst_pts[:, 0]), np.std(dst_pts[:, 1])

                is_2d_patch = (src_std_x > 10.0 and src_std_y > 10.0) and (dst_std_x > 10.0 and dst_std_y > 10.0) and not is_elongated_strip

                # RANSAC Affine / Homography Verification for isolated cloned patches
                if len(src_pts) >= 4 and is_2d_patch and is_compact_patch and is_disjoint and not is_harmonic_periodic:
                    try:
                        H, inliers = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 4.0)
                        if inliers is not None:
                            inlier_count = int(np.sum(inliers))
                            if inlier_count >= self.config.min_cluster_size:
                                pts = []
                                for idx, inl in enumerate(inliers.flatten()):
                                    if inl:
                                        pts.append(cluster_matches[idx][0])
                                        pts.append(cluster_matches[idx][1])
                                verified_clusters.append(pts)
                                max_inlier_count = max(max_inlier_count, inlier_count)
                    except Exception:
                        pass
                elif is_2d_patch and not is_elongated_strip and not is_harmonic_periodic and is_compact_patch and is_disjoint and len(src_pts) >= 6:
                    pts = [pt for m in cluster_matches for pt in m]
                    verified_clusters.append(pts)
                    max_inlier_count = max(max_inlier_count, len(cluster_matches) // 2)

        total_valid = len(valid_matches)
        consistency_score = float(max_inlier_count / max(total_valid, 1))

        return verified_clusters, max_inlier_count, consistency_score, is_harmonic_periodic

    def analyze(self, image_rgb: np.ndarray) -> Dict[str, Any]:
        """
        Executes copy-move forgery detection on an RGB image.

        Returns:
            Dict containing:
                score_percentage (float): Tampering likelihood (0 to 100%)
                details (str): Forensic interpretation
                metrics (dict): Keypoint count, valid matches, cluster metrics
                annotated_image (np.ndarray): Image with plotted matches and hulls (RGB uint8)
                heatmap_rgb (np.ndarray): Copy-move spatial density heatmap (RGB uint8)
        """
        h, w, _ = image_rgb.shape
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

        detector, matcher, is_sift = self._get_detector_and_matcher()
        keypoints, descriptors = detector.detectAndCompute(gray, None)

        valid_matches: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []

        if descriptors is not None and len(keypoints) >= 4 and len(descriptors) >= 4:
            if not is_sift and descriptors.dtype != np.uint8:
                descriptors = descriptors.astype(np.uint8)
            elif is_sift and descriptors.dtype != np.float32:
                descriptors = descriptors.astype(np.float32)

            # k-NN Matching with k=3 (descriptor matched against itself has k=1 as self at distance 0)
            try:
                knn_matches = matcher.knnMatch(descriptors, descriptors, k=3)
            except Exception:
                knn_matches = []

            min_dist = self.config.min_spatial_distance
            seen_pairs = set()

            for m in knn_matches:
                # Filter out self match (queryIdx == trainIdx)
                valid_m = [match for match in m if match.queryIdx != match.trainIdx]
                if len(valid_m) >= 2:
                    m1, m2 = valid_m[0], valid_m[1]
                    # Lowe's ratio test
                    if m1.distance < self.config.ratio_threshold * m2.distance or m1.distance < 5.0:
                        pt1 = keypoints[m1.queryIdx].pt
                        pt2 = keypoints[m1.trainIdx].pt
                        
                        # Spatial distance check (ignore immediate neighborhood)
                        spatial_dist = np.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])
                        if spatial_dist >= min_dist:
                            pair_key = (min(m1.queryIdx, m1.trainIdx), max(m1.queryIdx, m1.trainIdx))
                            if pair_key not in seen_pairs:
                                seen_pairs.add(pair_key)
                                valid_matches.append((pt1, pt2))
                elif len(valid_m) == 1:
                    m1 = valid_m[0]
                    if m1.distance < 15.0:
                        pt1 = keypoints[m1.queryIdx].pt
                        pt2 = keypoints[m1.trainIdx].pt
                        spatial_dist = np.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])
                        if spatial_dist >= min_dist:
                            pair_key = (min(m1.queryIdx, m1.trainIdx), max(m1.queryIdx, m1.trainIdx))
                            if pair_key not in seen_pairs:
                                seen_pairs.add(pair_key)
                                valid_matches.append((pt1, pt2))

        # Cluster analysis with 2D RANSAC and 1D periodic texture filter
        clusters, max_cluster_size, consistency_score, is_periodic_texture = self._cluster_matches(valid_matches, h, w)

        # Generate spatial density heatmap
        density_mask = np.zeros((h, w), dtype=np.float32)
        for p1, p2 in valid_matches:
            cv2.circle(density_mask, (int(round(p1[0])), int(round(p1[1]))), radius=20, color=1.0, thickness=-1)
            cv2.circle(density_mask, (int(round(p2[0])), int(round(p2[1]))), radius=20, color=1.0, thickness=-1)

        # Smooth density mask
        if np.max(density_mask) > 0:
            density_mask = cv2.GaussianBlur(density_mask, (31, 31), 0)
            norm_density = (density_mask / np.max(density_mask) * 255.0).astype(np.uint8)
        else:
            norm_density = np.zeros((h, w), dtype=np.uint8)

        heatmap_rgb = create_heatmap(norm_density, cv2.COLORMAP_JET)

        # Score computation (0 to 100%)
        score = 0.0
        total_matches = len(valid_matches)

        if max_cluster_size >= self.config.min_cluster_size and not is_periodic_texture:
            # Genuine verified 2D clone cluster
            cluster_factor = min(1.0, max_cluster_size / 12.0)
            score = 55.0 + (cluster_factor * 35.0) + (consistency_score * 10.0)
        elif is_periodic_texture:
            # 1D periodic architectural background (e.g. wooden slats, blinds, brick lines)
            score = min(18.0, total_matches * 0.3)
        elif len(clusters) > 0:
            score = min(35.0, max_cluster_size * 8.0)
        elif total_matches > 15:
            score = min(25.0, (total_matches / 25.0) * 25.0)
        elif total_matches > 0:
            score = min(15.0, total_matches * 1.5)

        score_percentage = float(np.clip(round(score, 1), 0.0, 100.0))

        # Forensic details description
        if is_periodic_texture:
            details = (
                f"Natural 1D periodic background texture detected ({total_matches} harmonic keypoints along architectural lines). "
                f"No 2D object clone forgery found."
            )
        elif score_percentage > 70.0:
            details = (
                f"Strong copy-move duplication identified: {total_matches} cross-spatial matching pairs "
                f"forming {len(clusters)} coherent displacement cluster(s) with 2D geometric consistency. "
                f"High confidence clone forgery detected."
            )
        elif score_percentage > 35.0:
            details = (
                f"Potential copy-move artifacts observed: {total_matches} spatially separated matching keypoint pairs. "
                f"Minor clustering suggests possible cloned texture or repetitive pattern."
            )
        else:
            details = (
                f"No significant duplicated keypoint clusters detected ({total_matches} isolated candidate matches). "
                f"Consistent with natural non-repetitive scene geometry."
            )

        # Generate annotated image
        annotated_image = draw_copy_move_annotations(image_rgb, valid_matches, clusters)

        return {
            "score_percentage": score_percentage,
            "details": details,
            "metrics": {
                "total_keypoints_detected": len(keypoints),
                "valid_match_pairs": total_matches,
                "coherent_clusters_count": len(clusters),
                "max_cluster_size": max_cluster_size,
                "displacement_consistency": round(consistency_score, 3),
            },
            "annotated_image": annotated_image,
            "heatmap_rgb": heatmap_rgb,
            "matches": valid_matches,
        }
