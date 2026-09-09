# MorphSpot: Multi-Modal Digital Image Forensics & Splicing Detection Framework

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-5.0+-orange.svg)](https://opencv.org/)

**MorphSpot** is a modular Python digital image forensics framework engineered to detect whether an input image has been tampered, morphed, spliced, cloned, or digitally manipulated. It employs computer vision algorithms, high-frequency residual analysis, and invariant keypoint clustering to generate a structured JSON forensic report, localized heatmap masks, and an overall **Morphed / Tampered Probability Score (0% to 100%)**.

---

## Key Forensic Detection Modules

| Module | Core Technique | Purpose |
| :--- | :--- | :--- |
| **Error Level Analysis (ELA)** | Multi-quality JPEG DCT recompression & variance disparity | Detects differing compression histories, uncompressed inserts, and selective re-saving. |
| **Noise Inconsistency** | High-pass median residual extraction & robust MAD z-scores | Identifies foreign spliced patches with sensor noise floor discrepancies. |
| **Copy-Move / Clone Forgery** | Invariant SIFT/ORB keypoints with displacement clustering | Detects duplicated regions, cloned objects, and stamp masks with spatial clustering. |
| **Edge & Blending Artifacts** | Sobel gradient transition profiles & contour sharpness | Uncovers abnormal step cut-outs, unnatural sharpness, and Gaussian feathering. |
| **Luminance & Color Variance** | CIE-$L^*a^*b^*$ 2D illumination polynomial surface fit | Detects conflicting lighting directions and chromatic temperature mismatches. |
| **Metadata & EXIF Audit** | EXIF, XMP, IPTC parsing for editing tool signatures | Identifies Photoshop, GIMP, Canva, PicsArt, AI tools (Midjourney, DALL-E) and timestamp anomalies. |

---

## Overall Manipulation Scoring & Verdicts

The Master Fusion Engine computes individual module scores $S_i \in [0, 100]$ and applies weighted aggregation and critical anomaly escalation:

- **`< 30%`** $\to$ **`Authentic / Untampered`**: Natural homogeneous noise floor, uniform compression, and coherent lighting.
- **`30% - 65%`** $\to$ **`Suspicious / Potential Edits`**: Moderate localized inconsistencies or metadata anomalies.
- **`> 65%`** $\to$ **`Morphed / Tampered`**: High-confidence digital manipulation (splicing, clone clusters, or strong ELA disparity).

---

## Structured JSON Output Specification

```json
{
  "status": "success",
  "filename": "sample.jpg",
  "tampered_probability_percentage": 78.4,
  "verdict": "Morphed / Tampered",
  "confidence_level": "High",
  "forensic_breakdown": {
    "ela_analysis": {
      "score_percentage": 82.5,
      "details": "High error rate disparity detected around central boundary.",
      "metrics": {
        "global_mean_error": 3.42,
        "global_std_error": 2.81,
        "peak_error": 48.2,
        "disparity_cv": 1.45,
        "anomalous_patch_ratio": 0.125
      }
    },
    "noise_consistency": {
      "score_percentage": 74.0,
      "details": "Abnormal variance in local high-frequency residuals.",
      "metrics": {
        "median_noise_std": 3.82,
        "noise_mad": 0.94,
        "max_z_score": 5.21,
        "outlier_patch_ratio": 0.142
      }
    },
    "copy_move_detection": {
      "score_percentage": 45.0,
      "details": "Minor matching keypoint clusters found.",
      "metrics": {
        "total_keypoints_detected": 1420,
        "valid_match_pairs": 8,
        "coherent_clusters_count": 1,
        "max_cluster_size": 4
      }
    },
    "edge_sharpness_inconsistency": {
      "score_percentage": 68.2,
      "details": "Unnatural gradient transition along suspected splice contours."
    },
    "metadata_analysis": {
      "has_exif": true,
      "software_detected": "Adobe Photoshop 2024",
      "flagged": true,
      "warnings": [
        "Known manipulation/editing software signature detected: 'Adobe Photoshop 2024'"
      ]
    }
  },
  "summary": "The image shows significant compression artifact mismatch and high-frequency noise variance consistent with digital splicing.",
  "annotated_mask_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
```

---

## Quickstart & Installation

```bash
# Clone or navigate to the project directory
cd image_forensics

# Install dependencies
pip install -r requirements.txt
```

---

## Running the Web API & Interactive Dashboard

Start the FastAPI server:
```bash
python -m uvicorn app.api:app --host 127.0.0.1 --port 8000 --reload
```

- **Interactive Forensic Dashboard UI:** Navigate to `http://127.0.0.1:8000/`
- **Interactive Swagger / OpenAPI Docs:** Navigate to `http://127.0.0.1:8000/docs`

---

## Using the CLI Tool

Analyze a single image:
```bash
python cli.py --image path/to/sample.jpg --output-dir ./results --save-masks
```

Batch analyze an entire directory:
```bash
python cli.py --dir path/to/dataset/ --output-dir ./batch_results
```

Output raw JSON directly to stdout:
```bash
python cli.py --image path/to/sample.jpg --json-only
```

---

## Python Programmatic Usage

```python
from app.engine import ForensicEngine
from app.config import DEFAULT_CONFIG

# Initialize engine
engine = ForensicEngine(DEFAULT_CONFIG)

# Analyze an image (accepts file path, PIL Image, or raw bytes)
report = engine.analyze(
    source="path/to/suspect_image.jpg",
    filename="suspect_image.jpg",
    include_all_visuals=True
)

print(f"Tampered Probability: {report['tampered_probability_percentage']}%")
print(f"Verdict: {report['verdict']}")
print(f"Confidence: {report['confidence_level']}")
```

---

## Running Tests

```bash
python -m unittest discover tests
```
