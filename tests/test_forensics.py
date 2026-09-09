"""
Unit and Integration Test Suite for MorphSpot Forensic Engine.
"""
import os
import sys
import unittest
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import DEFAULT_CONFIG, ForensicConfig
from app.engine import ForensicEngine
from app.modules.ela import ELADetector
from app.modules.noise import NoiseDetector
from app.modules.copy_move import CopyMoveDetector
from app.modules.edges import EdgeInconsistencyDetector
from app.modules.luminance import LuminanceDetector
from app.modules.metadata import MetadataAuditor
from app.api import app
from tests.generate_samples import generate_fixtures


class TestForensicModules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "sample_fixtures")
        cls.fixtures = generate_fixtures(fixtures_dir)
        cls.engine = ForensicEngine(DEFAULT_CONFIG)
        cls.client = TestClient(app)

    def test_ela_detector(self):
        detector = ELADetector(DEFAULT_CONFIG.ela)
        img_arr = np.array(Image.open(self.fixtures["authentic"]).convert("RGB"))
        result = detector.analyze(img_arr)

        self.assertIn("score_percentage", result)
        self.assertTrue(0.0 <= result["score_percentage"] <= 100.0)
        self.assertIn("details", result)
        self.assertIn("metrics", result)
        self.assertIsInstance(result["heatmap_rgb"], np.ndarray)
        self.assertEqual(result["heatmap_rgb"].shape[:2], img_arr.shape[:2])

    def test_noise_detector(self):
        detector = NoiseDetector(DEFAULT_CONFIG.noise)
        img_arr = np.array(Image.open(self.fixtures["spliced"]).convert("RGB"))
        result = detector.analyze(img_arr)

        self.assertIn("score_percentage", result)
        self.assertTrue(0.0 <= result["score_percentage"] <= 100.0)
        self.assertIn("median_noise_std", result["metrics"])
        self.assertIn("max_z_score", result["metrics"])
        # Spliced fixture has high noise variance
        self.assertGreater(result["score_percentage"], 30.0)

    def test_copy_move_detector(self):
        detector = CopyMoveDetector(DEFAULT_CONFIG.copy_move)
        img_arr = np.array(Image.open(self.fixtures["copy_move"]).convert("RGB"))
        result = detector.analyze(img_arr)

        self.assertIn("score_percentage", result)
        self.assertTrue(0.0 <= result["score_percentage"] <= 100.0)
        self.assertIn("valid_match_pairs", result["metrics"])
        self.assertIn("coherent_clusters_count", result["metrics"])
        # Copy-move sample has cloned stamp
        self.assertGreaterEqual(result["metrics"]["valid_match_pairs"], 4)
        self.assertGreater(result["score_percentage"], 40.0)

    def test_edge_detector(self):
        detector = EdgeInconsistencyDetector(DEFAULT_CONFIG.edges)
        img_arr = np.array(Image.open(self.fixtures["spliced"]).convert("RGB"))
        result = detector.analyze(img_arr)

        self.assertIn("score_percentage", result)
        self.assertTrue(0.0 <= result["score_percentage"] <= 100.0)
        self.assertIn("sharpness_cv", result["metrics"])
        self.assertEqual(result["heatmap_rgb"].shape[:2], img_arr.shape[:2])

    def test_luminance_detector(self):
        detector = LuminanceDetector(DEFAULT_CONFIG.luminance)
        img_arr = np.array(Image.open(self.fixtures["authentic"]).convert("RGB"))
        result = detector.analyze(img_arr)

        self.assertIn("score_percentage", result)
        self.assertTrue(0.0 <= result["score_percentage"] <= 100.0)
        self.assertIn("lum_residual_mean", result["metrics"])

    def test_metadata_auditor(self):
        auditor = MetadataAuditor(DEFAULT_CONFIG.metadata)
        
        # Test authentic (clean)
        auth_img = Image.open(self.fixtures["authentic"])
        auth_res = auditor.analyze(auth_img)
        self.assertFalse(auth_res["flagged"])

        # Test photoshop metadata
        meta_img = Image.open(self.fixtures["metadata_tampered"])
        meta_res = auditor.analyze(meta_img)
        self.assertTrue(meta_res["flagged"])
        self.assertIn("photoshop", meta_res["software_detected"].lower())

    def test_master_engine_report_schema(self):
        report = self.engine.analyze(self.fixtures["spliced"], filename="spliced_test.jpg", include_all_visuals=True)

        # Check top-level JSON fields
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["filename"], "spliced_test.jpg")
        self.assertIn("tampered_probability_percentage", report)
        self.assertTrue(0.0 <= report["tampered_probability_percentage"] <= 100.0)
        self.assertIn(report["verdict"], ["Authentic / Untampered", "Suspicious / Potential Edits", "Morphed / Tampered"])
        self.assertIn(report["confidence_level"], ["High", "Medium", "Low"])
        self.assertIn("forensic_breakdown", report)
        self.assertIn("summary", report)
        self.assertTrue(report["annotated_mask_base64"].startswith("data:image/"))

        # Check breakdown modules
        bd = report["forensic_breakdown"]
        for key in ["ela_analysis", "noise_consistency", "copy_move_detection", "edge_sharpness_inconsistency"]:
            self.assertIn(key, bd)
            self.assertIn("score_percentage", bd[key])
            self.assertIn("details", bd[key])

        self.assertIn("metadata_analysis", bd)
        self.assertIn("software_detected", bd["metadata_analysis"])
        self.assertIn("flagged", bd["metadata_analysis"])

    def test_api_endpoints(self):
        # Health check
        res_health = self.client.get("/api/v1/health")
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.json()["status"], "healthy")

        # Analyze upload
        with open(self.fixtures["authentic"], "rb") as f:
            res_upload = self.client.post(
                "/api/v1/analyze",
                files={"file": ("authentic.jpg", f, "image/jpeg")},
                data={"include_visuals": "true"}
            )
        self.assertEqual(res_upload.status_code, 200)
        json_data = res_upload.json()
        self.assertEqual(json_data["status"], "success")
        self.assertIn("tampered_probability_percentage", json_data)

        # Single module endpoint
        with open(self.fixtures["spliced"], "rb") as f:
            res_mod = self.client.post(
                "/api/v1/analyze/module/ela",
                files={"file": ("spliced.jpg", f, "image/jpeg")}
            )
        self.assertEqual(res_mod.status_code, 200)
        mod_data = res_mod.json()
        self.assertIn("score_percentage", mod_data)
        self.assertIn("heatmap_base64", mod_data)


if __name__ == "__main__":
    unittest.main()
