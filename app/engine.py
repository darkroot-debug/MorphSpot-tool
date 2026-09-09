"""
Master Forensic Engine and Multi-Detector Fusion Pipeline.

Coordinates Error Level Analysis, Noise Residual Analysis, Copy-Move Forgery Detection,
Edge Blending Inconsistencies, Luminance Variance, and Metadata Auditing into a unified
forensic report matching the required JSON schema.
"""
import datetime
import io
from typing import Any, Dict, Optional, Union
import uuid
import cv2
import numpy as np
from PIL import Image

from app.config import ForensicConfig, DEFAULT_CONFIG
from app.modules.ela import ELADetector
from app.modules.noise import NoiseDetector
from app.modules.copy_move import CopyMoveDetector
from app.modules.edges import EdgeInconsistencyDetector
from app.modules.luminance import LuminanceDetector
from app.modules.metadata import MetadataAuditor
from app.utils.image_io import compute_image_sha256, load_image
from app.utils.visualizer import (
    create_blended_overlay,
    create_heatmap,
    encode_image_to_base64,
    normalize_to_uint8
)
from app.utils.reporter import generate_forensic_html_certificate


class ForensicEngine:
    """Master orchestrator for digital image manipulation and tampering analysis."""

    def __init__(self, config: ForensicConfig = DEFAULT_CONFIG):
        self.config = config
        self.ela_detector = ELADetector(config.ela)
        self.noise_detector = NoiseDetector(config.noise)
        self.copy_move_detector = CopyMoveDetector(config.copy_move)
        self.edge_detector = EdgeInconsistencyDetector(config.edges)
        self.luminance_detector = LuminanceDetector(config.luminance)
        self.metadata_auditor = MetadataAuditor(config.metadata)

    def _determine_verdict(self, score: float) -> str:
        """Determines the classification verdict label."""
        if score < self.config.authentic_threshold:
            return "Authentic / Untampered"
        elif score <= self.config.suspicious_threshold:
            return "Suspicious / Potential Edits"
        else:
            return "Morphed / Tampered"

    def _determine_authenticity_grade(self, score: float) -> str:
        """Determines the forensic authenticity letter grade based on overall tampered probability."""
        if score < 20.0:
            return "Grade A (Pristine / Authentic)"
        elif score < 40.0:
            return "Grade B (Authentic / Minor Baseline Variance)"
        elif score <= 65.0:
            return "Grade C (Suspicious / Potential Manipulation)"
        elif score < 85.0:
            return "Grade D (High Tampering Discrepancies)"
        else:
            return "Grade F (Severely Manipulated / Spliced / Cloned)"

    def _determine_confidence(
        self,
        scores: Dict[str, float],
        final_score: float,
        copy_move_clusters: int,
        metadata_flagged: bool
    ) -> str:
        """Calculates confidence rating based on detector consensus and evidence strength."""
        high_signals = sum(1 for s in scores.values() if s > 65.0)
        moderate_signals = sum(1 for s in scores.values() if s > 40.0)

        if final_score >= 70.0:
            if high_signals >= 2 or copy_move_clusters > 0 or metadata_flagged:
                return "High"
            return "Medium"
        elif final_score < 30.0:
            if all(s < 35.0 for s in scores.values()):
                return "High"
            return "Medium"
        else:
            if moderate_signals >= 2:
                return "Medium"
            return "Low"

    def _generate_summary(
        self,
        verdict: str,
        final_score: float,
        ela_score: float,
        noise_score: float,
        copy_score: float,
        edge_score: float,
        meta_flagged: bool,
        meta_software: str
    ) -> str:
        """Generates a natural-language summary synthesizing all findings."""
        findings = []

        if copy_score > 60.0:
            findings.append("cloned/duplicated keypoint clusters (copy-move forgery)")
        if ela_score > 65.0:
            findings.append("compression artifact mismatch from image splicing")
        if noise_score > 65.0:
            findings.append("high-frequency sensor noise variance disparity")
        if edge_score > 65.0:
            findings.append("unnatural gradient transitions along object contours")
        if meta_flagged and meta_software != "None":
            findings.append(f"metadata traces of editing software ({meta_software})")

        if verdict == "Morphed / Tampered":
            if findings:
                evidence_str = " and ".join(findings[:3])
                return f"The image exhibits significant digital manipulation, including {evidence_str}, confirming tampering."
            return "The image shows strong multi-modal forensic anomalies consistent with digital splicing or morphing."
        elif verdict == "Suspicious / Potential Edits":
            if findings:
                return f"The image exhibits localized anomalies such as {findings[0]}, suggesting potential digital retouching or re-compression."
            return "The image contains moderate forensic inconsistencies that warrant manual inspection."
        else:
            return "The image demonstrates consistent compression, homogeneous sensor noise, and natural edge gradients, indicating an authentic, untampered photo."

    def _create_composite_mask(
        self,
        image_rgb: np.ndarray,
        ela_diff: np.ndarray,
        noise_res: np.ndarray,
        edge_mask: np.ndarray,
        copy_move_annotated: np.ndarray,
        copy_move_score: float
    ) -> np.ndarray:
        """
        Synthesizes individual detector outputs into a single high-impact visual composite heatmap.
        """
        h, w, _ = image_rgb.shape

        # Normalize and align layers
        ela_norm = cv2.resize(ela_diff, (w, h)).astype(np.float32) / 255.0
        noise_norm = cv2.resize(noise_res, (w, h)).astype(np.float32) / 255.0

        # Edge dilation for visual prominence
        edge_dilated = cv2.dilate(edge_mask, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
        edge_norm = cv2.resize(edge_dilated, (w, h)).astype(np.float32) / 255.0

        # Weighted combination of anomaly fields
        composite_field = (ela_norm * 0.45) + (noise_norm * 0.35) + (edge_norm * 0.20)
        composite_field = cv2.GaussianBlur(composite_field, (15, 15), 0)
        composite_uint8 = normalize_to_uint8(composite_field, (2.0, 98.0))

        # Colorize composite heatmap
        heatmap_rgb = create_heatmap(composite_uint8, cv2.COLORMAP_JET)

        # Blend over original image
        blended = create_blended_overlay(image_rgb, heatmap_rgb, alpha=0.50)

        # If strong copy-move matches exist, blend the annotated arrows onto the final mask
        if copy_move_score > 35.0:
            # Alpha blend copy-move vectors
            blended = cv2.addWeighted(blended, 0.70, copy_move_annotated, 0.30, 0)

        return blended

    def analyze(
        self,
        source: Union[str, bytes, io.BytesIO, Image.Image],
        filename: str = "image.jpg",
        include_all_visuals: bool = False
    ) -> Dict[str, Any]:
        """
        Runs the full forensic detection pipeline on an image.

        Args:
            source: Image file path, raw bytes, BytesIO stream, or PIL Image.
            filename: Name of the input file for reference.
            include_all_visuals: If True, includes individual base64 masks for all modules.

        Returns:
            Structured JSON forensic report dictionary matching specifications.
        """
        # 1. Load image and extract metadata
        image_rgb, pil_img, raw_exif = load_image(source, max_dimension=self.config.max_dimension)

        # 2. Execute Detection Modules
        ela_res = self.ela_detector.analyze(image_rgb)
        noise_res = self.noise_detector.analyze(image_rgb)
        copy_res = self.copy_move_detector.analyze(image_rgb)
        edge_res = self.edge_detector.analyze(image_rgb)
        lum_res = self.luminance_detector.analyze(image_rgb)
        meta_res = self.metadata_auditor.analyze(pil_img, raw_exif)

        # 3. Extract individual scores
        scores = {
            "ela": ela_res["score_percentage"],
            "noise": noise_res["score_percentage"],
            "copy_move": copy_res["score_percentage"],
            "edges": edge_res["score_percentage"],
            "luminance": lum_res["score_percentage"],
        }

        # 4. Multi-Modal Fusion & Aggregation Algorithm
        w = self.config.weights
        base_score = (
            scores["ela"] * w.ela +
            scores["noise"] * w.noise +
            scores["copy_move"] * w.copy_move +
            scores["edges"] * w.edges +
            scores["luminance"] * w.luminance
        )

        # Camera verification discount: if authentic camera hardware tags are present and clean
        if meta_res.get("camera_verified", False) and not meta_res["flagged"]:
            base_score *= 0.75

        # Ambient baseline suppression: when no individual module indicates tampering (<40%)
        max_forensic_signal = max(scores["ela"], scores["noise"], scores["copy_move"], scores["edges"])
        if max_forensic_signal < 45.0 and not meta_res["flagged"]:
            base_score = max(0.0, (base_score ** 1.15) * 0.65)

        # Apply critical anomaly escalations
        escalation = 0.0
        # High copy-move match is unequivocal evidence of clone forgery
        if scores["copy_move"] >= 65.0:
            escalation += w.copy_move_high_confidence_boost * (scores["copy_move"] / 100.0)

        # Editing software signature in EXIF boosts tampering probability
        if meta_res["flagged"]:
            escalation += w.metadata_flag_boost

        # Multiple concurring high anomaly signals trigger synergy boost
        high_signals = sum(1 for s in scores.values() if s > 65.0)
        if high_signals >= 2:
            escalation += 10.0

        final_tampered_prob = float(np.clip(round(base_score + escalation, 1), 0.0, 100.0))

        # 5. Determine Verdict, Grade & Confidence
        verdict = self._determine_verdict(final_tampered_prob)
        grade = self._determine_authenticity_grade(final_tampered_prob)
        confidence = self._determine_confidence(
            scores,
            final_tampered_prob,
            copy_res["metrics"]["coherent_clusters_count"],
            meta_res["flagged"]
        )

        # 6. Generate Natural Language Summary
        summary = self._generate_summary(
            verdict=verdict,
            final_score=final_tampered_prob,
            ela_score=scores["ela"],
            noise_score=scores["noise"],
            copy_score=scores["copy_move"],
            edge_score=scores["edges"],
            meta_flagged=meta_res["flagged"],
            meta_software=meta_res["software_detected"]
        )

        # 7. Generate Visual Anomaly Heatmap / Mask
        composite_mask = self._create_composite_mask(
            image_rgb=image_rgb,
            ela_diff=ela_res["difference_map"],
            noise_res=noise_res["residual_map"],
            edge_mask=edge_res["edge_mask"],
            copy_move_annotated=copy_res["annotated_image"],
            copy_move_score=scores["copy_move"]
        )
        annotated_mask_b64 = encode_image_to_base64(composite_mask, format="JPEG", quality=85)

        # 8. Cryptographic Hash, Timestamps & Identifiers
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        report_id = f"MS-{now_utc.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        sha256_hash = compute_image_sha256(source)
        dims = {
            "width": int(pil_img.width),
            "height": int(pil_img.height),
            "channels": int(image_rgb.shape[2]) if len(image_rgb.shape) > 2 else 1
        }
        meta_score = float(meta_res.get("score_percentage", 85.0 if meta_res["flagged"] else (10.0 if meta_res.get("camera_verified", False) else 25.0)))

        # 9. Build Structured Report matching the required JSON schema
        report: Dict[str, Any] = {
            "status": "success",
            "report_id": report_id,
            "timestamp": now_utc.isoformat(),
            "filename": filename,
            "sha256_hash": sha256_hash,
            "image_dimensions": dims,
            "tampered_probability_percentage": final_tampered_prob,
            "authenticity_grade": grade,
            "verdict": verdict,
            "confidence_level": confidence,
            "forensic_breakdown": {
                "ela_analysis": {
                    "score_percentage": scores["ela"],
                    "details": ela_res["details"],
                    "metrics": ela_res["metrics"],
                },
                "noise_consistency": {
                    "score_percentage": scores["noise"],
                    "details": noise_res["details"],
                    "metrics": noise_res["metrics"],
                },
                "copy_move_detection": {
                    "score_percentage": scores["copy_move"],
                    "details": copy_res["details"],
                    "metrics": copy_res["metrics"],
                },
                "edge_sharpness_inconsistency": {
                    "score_percentage": scores["edges"],
                    "details": edge_res["details"],
                    "metrics": edge_res["metrics"],
                },
                "luminance_gradient_variance": {
                    "score_percentage": scores["luminance"],
                    "details": lum_res["details"],
                    "metrics": lum_res["metrics"],
                },
                "metadata_analysis": {
                    "score_percentage": meta_score,
                    "has_exif": meta_res["has_exif"],
                    "software_detected": meta_res["software_detected"],
                    "flagged": meta_res["flagged"],
                    "warnings": meta_res["warnings"],
                    "details": meta_res["details"],
                },
            },
            "summary": summary,
            "annotated_mask_base64": annotated_mask_b64,
        }

        # Optional full visual breakdown for interactive UI / deep debugging
        if include_all_visuals:
            report["visual_breakdown"] = {
                "original_base64": encode_image_to_base64(image_rgb, format="JPEG", quality=85),
                "ela_heatmap_base64": encode_image_to_base64(ela_res["heatmap_rgb"], format="JPEG", quality=85),
                "noise_heatmap_base64": encode_image_to_base64(noise_res["heatmap_rgb"], format="JPEG", quality=85),
                "copy_move_annotated_base64": encode_image_to_base64(copy_res["annotated_image"], format="JPEG", quality=85),
                "edge_heatmap_base64": encode_image_to_base64(edge_res["heatmap_rgb"], format="JPEG", quality=85),
                "luminance_heatmap_base64": encode_image_to_base64(lum_res["heatmap_rgb"], format="JPEG", quality=85),
            }

        return report

    def generate_certificate(self, report_data: Dict[str, Any]) -> str:
        """
        Generates a standalone, executive-grade forensic examination certificate in HTML.
        """
        return generate_forensic_html_certificate(report_data)
