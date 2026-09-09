"""
FastAPI REST API Backend for Digital Image Forensics & Manipulation Detection.
"""
import io
from typing import Optional
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os

from app.engine import ForensicEngine
from app.config import DEFAULT_CONFIG
from app.utils.image_io import load_image
from app.utils.visualizer import encode_image_to_base64


app = FastAPI(
    title="Image Forensics & Splicing Detection API",
    description="Computer Vision & Forensic Analysis API to detect tampered, morphed, spliced, and cloned images.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for seamless integration with any frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Engine
engine = ForensicEngine(DEFAULT_CONFIG)

# Mount static folder if it exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


class Base64AnalyzeRequest(BaseModel):
    image_base64: str
    filename: Optional[str] = "input_image.jpg"
    include_visuals: Optional[bool] = True


@app.get("/api/v1/health", summary="API Health Check")
async def health_check():
    """Health check endpoint returning system status and enabled detector modules."""
    return {
        "status": "healthy",
        "engine_version": "1.0.0",
        "detectors": [
            "Error Level Analysis (ELA)",
            "Noise Inconsistency (Wavelet / Median Residuals)",
            "Copy-Move / Clone Forgery (SIFT / Keypoint Clustering)",
            "Edge Inconsistency & Blending Artifacts (Sobel / Canny)",
            "Luminance & Color Gradient Variance (CIE-Lab / Surface Fit)",
            "Metadata & EXIF Software Audit"
        ]
    }


@app.post("/api/v1/analyze", summary="Analyze Uploaded Image File")
async def analyze_image_file(
    file: UploadFile = File(..., description="Image file (JPG, PNG, WEBP, TIFF, BMP)"),
    include_visuals: bool = Form(True, description="Whether to include full visual breakdown masks")
):
    """
    Analyzes an uploaded image for digital manipulation, morphing, and splicing.
    Returns the complete structured forensic report, overall tampered probability score,
    module breakdowns, and base64-encoded visual heatmaps.
    """
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Empty file uploaded.")

        filename = file.filename or "uploaded_image.jpg"
        report = engine.analyze(
            source=contents,
            filename=filename,
            include_all_visuals=include_visuals
        )
        return JSONResponse(content=report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forensic analysis failed: {str(e)}")


@app.post("/api/v1/analyze/base64", summary="Analyze Base64 Encoded Image")
async def analyze_image_base64(payload: Base64AnalyzeRequest):
    """
    Analyzes a base64-encoded image string (data:image/... or raw base64).
    """
    try:
        report = engine.analyze(
            source=payload.image_base64,
            filename=payload.filename or "base64_image.jpg",
            include_all_visuals=payload.include_visuals
        )
        return JSONResponse(content=report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forensic analysis failed: {str(e)}")


@app.post("/api/v1/analyze/module/{module_name}", summary="Run Specific Forensic Module")
async def run_single_module(
    module_name: str,
    file: UploadFile = File(...)
):
    """
    Runs a single targeted forensic detector on an image:
    `ela`, `noise`, `copy_move`, `edges`, `luminance`, `metadata`.
    """
    module_key = module_name.lower().strip()
    valid_modules = ["ela", "noise", "copy_move", "edges", "luminance", "metadata"]
    if module_key not in valid_modules:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid module '{module_name}'. Choose from: {valid_modules}"
        )

    try:
        contents = await file.read()
        image_rgb, pil_img, raw_exif = load_image(contents)

        if module_key == "ela":
            res = engine.ela_detector.analyze(image_rgb)
            res["heatmap_base64"] = encode_image_to_base64(res.pop("heatmap_rgb"))
            res.pop("difference_map", None)
            return res
        elif module_key == "noise":
            res = engine.noise_detector.analyze(image_rgb)
            res["heatmap_base64"] = encode_image_to_base64(res.pop("heatmap_rgb"))
            res.pop("residual_map", None)
            return res
        elif module_key == "copy_move":
            res = engine.copy_move_detector.analyze(image_rgb)
            res["annotated_base64"] = encode_image_to_base64(res.pop("annotated_image"))
            res["heatmap_base64"] = encode_image_to_base64(res.pop("heatmap_rgb"))
            res.pop("matches", None)
            return res
        elif module_key == "edges":
            res = engine.edge_detector.analyze(image_rgb)
            res["heatmap_base64"] = encode_image_to_base64(res.pop("heatmap_rgb"))
            res.pop("edge_mask", None)
            return res
        elif module_key == "luminance":
            res = engine.luminance_detector.analyze(image_rgb)
            res["heatmap_base64"] = encode_image_to_base64(res.pop("heatmap_rgb"))
            res.pop("residual_map", None)
            return res
        elif module_key == "metadata":
            return engine.metadata_auditor.analyze(pil_img, raw_exif)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Module analysis error: {str(e)}")


@app.post("/api/v1/report/certificate", summary="Export Forensic Examination Certificate Document")
async def export_certificate(report_data: dict):
    """
    Accepts an analysis report dictionary and renders a standalone, high-resolution
    forensic examination certificate in HTML (print/PDF ready).
    """
    try:
        html_doc = engine.generate_certificate(report_data)
        report_id = report_data.get("report_id", "MS-DOCUMENT")
        filename = f"Forensic_Certificate_{report_id}.html"
        return Response(
            content=html_doc,
            media_type="text/html",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate certificate: {str(e)}")


@app.post("/api/v1/analyze/certificate", summary="Analyze Image & Download Certificate Directly")
async def analyze_and_download_certificate(
    file: UploadFile = File(..., description="Image file to analyze and certify")
):
    """
    Direct single-step endpoint: uploads an image, executes full multi-modal forensic detection,
    and returns a downloadable forensic certificate document.
    """
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Empty file uploaded.")

        filename = file.filename or "uploaded_image.jpg"
        report = engine.analyze(source=contents, filename=filename, include_all_visuals=True)
        html_doc = engine.generate_certificate(report)
        report_id = report.get("report_id", "MS-DOCUMENT")
        
        return Response(
            content=html_doc,
            media_type="text/html",
            headers={
                "Content-Disposition": f'attachment; filename="Forensic_Certificate_{report_id}.html"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Certificate generation failed: {str(e)}")


@app.get("/", response_class=HTMLResponse, summary="Forensic Dashboard UI")
async def serve_dashboard():
    """Serves the interactive web forensic investigation dashboard."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h2>Image Forensics API is running. Visit <a href='/docs'>/docs</a> for Swagger UI.</h2>")


if __name__ == "__main__":
    uvicorn.run("app.api:app", host="127.0.0.1", port=8000, reload=True)
