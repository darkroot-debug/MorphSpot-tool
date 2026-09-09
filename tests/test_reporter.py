"""
Unit & Integration Tests for MorphSpot Forensic Certificate & Reporter Generator.
"""
import os
import sys
import unittest
from PIL import Image
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import DEFAULT_CONFIG
from app.engine import ForensicEngine
from app.api import app
from app.utils.image_io import compute_image_sha256
from app.utils.reporter import generate_forensic_html_certificate
from tests.generate_samples import generate_fixtures


class TestForensicReporter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "sample_fixtures")
        cls.fixtures = generate_fixtures(fixtures_dir)
        cls.engine = ForensicEngine(DEFAULT_CONFIG)
        cls.client = TestClient(app)

    def test_sha256_hash_computation(self):
        """Verify SHA-256 hash is correctly calculated for image paths and bytes."""
        auth_path = self.fixtures["authentic"]
        hash1 = compute_image_sha256(auth_path)
        self.assertIsInstance(hash1, str)
        self.assertEqual(len(hash1), 64)

        with open(auth_path, "rb") as f:
            bytes_data = f.read()
        hash2 = compute_image_sha256(bytes_data)
        self.assertEqual(hash1, hash2)

    def test_engine_report_enrichment(self):
        """Verify that engine.analyze() enriches report with report_id, sha256_hash, grade, timestamp, etc."""
        report = self.engine.analyze(
            source=self.fixtures["spliced"],
            filename="spliced_test.jpg",
            include_all_visuals=True
        )

        self.assertIn("report_id", report)
        self.assertTrue(report["report_id"].startswith("MS-"))
        self.assertIn("timestamp", report)
        self.assertIn("sha256_hash", report)
        self.assertEqual(len(report["sha256_hash"]), 64)
        self.assertIn("authenticity_grade", report)
        self.assertIn("image_dimensions", report)
        self.assertIn("width", report["image_dimensions"])
        self.assertIn("height", report["image_dimensions"])

        # Check all 6 modules have scores
        breakdown = report["forensic_breakdown"]
        self.assertIn("score_percentage", breakdown["ela_analysis"])
        self.assertIn("score_percentage", breakdown["noise_consistency"])
        self.assertIn("score_percentage", breakdown["copy_move_detection"])
        self.assertIn("score_percentage", breakdown["edge_sharpness_inconsistency"])
        self.assertIn("score_percentage", breakdown["luminance_gradient_variance"])
        self.assertIn("score_percentage", breakdown["metadata_analysis"])

    def test_html_certificate_generation(self):
        """Verify that generate_forensic_html_certificate generates valid, self-contained HTML."""
        report = self.engine.analyze(
            source=self.fixtures["copy_move"],
            filename="copy_move_sample.jpg",
            include_all_visuals=True
        )

        html_doc = generate_forensic_html_certificate(report)
        self.assertIsInstance(html_doc, str)
        self.assertIn("<!DOCTYPE html>", html_doc)
        self.assertIn(report["report_id"], html_doc)
        self.assertIn(report["sha256_hash"], html_doc)
        self.assertIn("Error Level Analysis", html_doc)
        self.assertIn("Noise Inconsistency", html_doc)
        self.assertIn("Copy-Move", html_doc)
        self.assertIn("Edge Sharpness", html_doc)
        self.assertIn("Luminance", html_doc)
        self.assertIn("EXIF", html_doc)
        self.assertIn("Provenance", html_doc)
        self.assertIn("@media print", html_doc)
        self.assertIn("data:image/", html_doc)  # Base64 visuals embedded

    def test_api_export_certificate_endpoint(self):
        """Verify POST /api/v1/report/certificate returns downloadable HTML file."""
        report = self.engine.analyze(
            source=self.fixtures["authentic"],
            filename="auth.jpg",
            include_all_visuals=True
        )

        response = self.client.post("/api/v1/report/certificate", json=report)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "text/html; charset=utf-8")
        self.assertIn("attachment", response.headers.get("content-disposition", ""))
        self.assertIn("<!DOCTYPE html>", response.text)
        self.assertIn(report["report_id"], response.text)

    def test_api_analyze_and_certificate_direct_endpoint(self):
        """Verify POST /api/v1/analyze/certificate directly analyzes and returns certificate."""
        with open(self.fixtures["spliced"], "rb") as f:
            response = self.client.post(
                "/api/v1/analyze/certificate",
                files={"file": ("spliced_upload.jpg", f, "image/jpeg")}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "text/html; charset=utf-8")
        self.assertIn("attachment", response.headers.get("content-disposition", ""))
        self.assertIn("<!DOCTYPE html>", response.text)
        self.assertIn("MorphSpot Digital Forensics", response.text)


if __name__ == "__main__":
    unittest.main()
