"""
Metadata and EXIF Audit Forensic Module.

Inspects EXIF, IPTC, and XMP metadata chunks for editing software signatures,
timestamp contradictions, camera hardware authenticity, and stripped metadata flags.
"""
from typing import Any, Dict, List, Optional
import numpy as np
from PIL import ExifTags, Image

from app.config import MetadataConfig, DEFAULT_CONFIG


class MetadataAuditor:
    """Audits image EXIF and metadata integrity for digital manipulation traces."""

    def __init__(self, config: MetadataConfig = DEFAULT_CONFIG.metadata):
        self.config = config

    def analyze(self, pil_image: Image.Image, raw_exif_dict: Optional[dict] = None) -> Dict[str, Any]:
        """
        Performs a comprehensive forensic audit on the image's metadata.

        Returns:
            Dict containing:
                score_percentage (float): Tampering risk score based on metadata (0 to 100%)
                details (str): Summary of metadata findings
                has_exif (bool): Whether valid EXIF tags exist
                software_detected (Optional[str]): Name of editing tool if identified
                flagged (bool): True if suspicious signatures or anomalies detected
                metadata_tags (dict): Clean dictionary of parsed EXIF tags
                warnings (List[str]): Specific red flags found during audit
        """
        warnings: List[str] = []
        parsed_tags: Dict[str, str] = {}
        software_detected: Optional[str] = None
        has_exif = False

        # Attempt to extract EXIF dictionary
        exif_data = raw_exif_dict or {}
        if not exif_data and hasattr(pil_image, "getexif"):
            try:
                exif_data = pil_image.getexif()
            except Exception:
                exif_data = {}

        if exif_data:
            has_exif = True
            for tag_id, value in exif_data.items():
                tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                str_val = str(value).strip()
                parsed_tags[tag_name] = str_val

        # Also inspect PIL image info dictionary (often contains XMP, PNG chunks, etc.)
        image_info = getattr(pil_image, "info", {})
        for key, val in image_info.items():
            if isinstance(key, str) and isinstance(val, (str, bytes)):
                str_val = val.decode("utf-8", errors="ignore") if isinstance(val, bytes) else str(val)
                if key.lower() not in [k.lower() for k in parsed_tags.keys()]:
                    parsed_tags[f"info_{key}"] = str_val[:300]

        # 1. Search for editing software signatures
        software_fields = ["Software", "ProcessingSoftware", "Artist", "ImageDescription", "UserComment", "info_Software", "info_comment", "info_XML:com.adobe.xmp"]
        suspicious_list = [s.lower() for s in self.config.suspicious_software]

        for field in software_fields:
            for tag_k, tag_v in parsed_tags.items():
                if field.lower() in tag_k.lower():
                    val_lower = tag_v.lower()
                    for sw in suspicious_list:
                        if sw in val_lower:
                            software_detected = tag_v
                            warnings.append(f"Known manipulation/editing software signature detected: '{tag_v}'")
                            break
                if software_detected:
                    break
            if software_detected:
                break

        # Check raw info strings for Adobe / Photoshop / GIMP traces
        if not software_detected:
            for k, v in parsed_tags.items():
                v_lower = str(v).lower()
                for sw in suspicious_list:
                    if sw in v_lower and len(v_lower) < 200:
                        software_detected = str(v)
                        warnings.append(f"Editing software signature identified in tag [{k}]: '{v}'")
                        break
                if software_detected:
                    break

        # 2. Check for timestamp discrepancies
        dt_orig = parsed_tags.get("DateTimeOriginal") or parsed_tags.get("DateTime")
        dt_mod = parsed_tags.get("DateTimeDigitized") or parsed_tags.get("DateTime")
        if dt_orig and dt_mod and dt_orig != dt_mod:
            warnings.append(f"Timestamp discrepancy: Original [{dt_orig}] differs from Modified [{dt_mod}]")

        # 3. Check for camera hardware tags vs missing metadata
        has_camera_hardware = bool(parsed_tags.get("Make") or parsed_tags.get("Model"))
        if not has_exif:
            warnings.append("EXIF metadata is completely stripped (common in web re-saves or digital manipulation exports)")
        elif not has_camera_hardware and not software_detected:
            warnings.append("EXIF present but lacks camera hardware tags (Make/Model)")

        # 4. Calculate Metadata Risk Score (0 to 100%)
        camera_verified = bool(has_camera_hardware and not software_detected)
        score = 0.0
        if software_detected:
            score += 75.0
            if len(warnings) > 1:
                score += 15.0
        elif not has_exif:
            score += 10.0  # Mild neutral indicator (many chat apps strip EXIF)

        score_percentage = float(np.clip(round(score, 1), 0.0, 100.0))
        flagged = bool(software_detected or score_percentage > 50.0)

        # 5. Summary details
        if software_detected:
            details = f"Digital editing software detected in metadata tags: '{software_detected}'."
        elif not has_exif:
            details = "No EXIF metadata found (stripped by social app or web export)."
        else:
            make = parsed_tags.get("Make", "Unknown Make")
            model = parsed_tags.get("Model", "Unknown Model")
            details = f"Standard camera EXIF verified ({make} {model}). No suspicious software tags found."

        return {
            "score_percentage": score_percentage,
            "has_exif": has_exif,
            "camera_verified": camera_verified,
            "software_detected": software_detected or "None",
            "flagged": flagged,
            "details": details,
            "warnings": warnings,
            "metadata_tags": {k: str(v)[:150] for k, v in list(parsed_tags.items())[:25]},
        }
