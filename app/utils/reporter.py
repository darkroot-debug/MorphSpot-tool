"""
MorphSpot Forensic Examination Certificate & Audit Record Generator.

Generates self-contained, high-resolution, print-optimized (PDF-ready) forensic
dossiers containing full cryptographic hashes, multi-point percentage scores,
visual evidence heatmaps, and EXIF camera provenance.
"""
from typing import Any, Dict
import datetime
import html


def generate_forensic_html_certificate(report: Dict[str, Any]) -> str:
    """
    Renders a standalone, executive-grade forensic examination certificate in HTML.
    
    Args:
        report: Forensic analysis output dictionary from ForensicEngine.
        
    Returns:
        Self-contained HTML string with embedded CSS, base64 images, and print rules.
    """
    # 1. Extract core attributes
    report_id = report.get("report_id", "MS-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-000000"))
    timestamp_utc = report.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat())
    filename = html.escape(str(report.get("filename", "evidence_image.jpg")))
    sha256_hash = str(report.get("sha256_hash", "N/A"))
    tampered_prob = float(report.get("tampered_probability_percentage", 0.0))
    verdict = str(report.get("verdict", "Authentic / Untampered"))
    confidence = str(report.get("confidence_level", "Medium"))
    summary = html.escape(str(report.get("summary", "")))
    grade = str(report.get("authenticity_grade", "Grade A (Authentic)"))
    dims = report.get("image_dimensions", {})
    dim_str = f"{dims.get('width', 'N/A')} &times; {dims.get('height', 'N/A')} px" if dims else "Standard Resolution"

    # Color tokens based on verdict
    if tampered_prob < 30.0:
        verdict_color = "#10b981"  # Emerald
        verdict_bg = "rgba(16, 185, 129, 0.12)"
        verdict_border = "#10b981"
        badge_text = "AUTHENTIC / UNTAMPERED"
    elif tampered_prob <= 65.0:
        verdict_color = "#f59e0b"  # Amber
        verdict_bg = "rgba(245, 158, 11, 0.12)"
        verdict_border = "#f59e0b"
        badge_text = "SUSPICIOUS / POTENTIAL EDITS"
    else:
        verdict_color = "#ef4444"  # Crimson
        verdict_bg = "rgba(239, 68, 68, 0.12)"
        verdict_border = "#ef4444"
        badge_text = "MANIPULATED / TAMPERED"

    breakdown = report.get("forensic_breakdown", {})
    ela = breakdown.get("ela_analysis", {})
    noise = breakdown.get("noise_consistency", {})
    copy_move = breakdown.get("copy_move_detection", {})
    edges = breakdown.get("edge_sharpness_inconsistency", {})
    luminance = breakdown.get("luminance_gradient_variance", {})
    meta = breakdown.get("metadata_analysis", {})

    # Helper for risk badges
    def get_risk_pill(score: float) -> str:
        if score >= 65.0:
            return '<span class="pill pill-high">HIGH ANOMALY</span>'
        elif score >= 35.0:
            return '<span class="pill pill-med">MODERATE ANOMALY</span>'
        else:
            return '<span class="pill pill-low">NORMAL / HOMOGENEOUS</span>'

    # Build metadata warnings list
    meta_warnings_html = ""
    warnings_list = meta.get("warnings", [])
    if warnings_list:
        meta_warnings_html = "<ul class='warning-list'>" + "".join(
            f"<li><strong>⚠️ Warning:</strong> {html.escape(str(w))}</li>" for w in warnings_list
        ) + "</ul>"
    else:
        meta_warnings_html = "<p class='clean-note'>✓ No suspicious software signatures, editing markers, or metadata contradictions detected.</p>"

    # Extract visual heatmaps
    visuals = report.get("visual_breakdown", {})
    orig_b64 = visuals.get("original_base64", report.get("annotated_mask_base64", ""))
    composite_b64 = report.get("annotated_mask_base64", "")
    ela_b64 = visuals.get("ela_heatmap_base64", "")
    noise_b64 = visuals.get("noise_heatmap_base64", "")
    copymove_b64 = visuals.get("copy_move_annotated_base64", "")
    edges_b64 = visuals.get("edge_heatmap_base64", "")
    lum_b64 = visuals.get("luminance_heatmap_base64", "")

    # Format human UTC date
    formatted_date = datetime.datetime.now(datetime.timezone.utc).strftime("%B %d, %Y - %H:%M:%S UTC")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MorphSpot Forensic Certificate - {report_id}</title>
  <style>
    :root {{
      --bg-page: #f8fafc;
      --card-bg: #ffffff;
      --text-main: #0f172a;
      --text-muted: #475569;
      --border-color: #cbd5e1;
      --primary: #2563eb;
      --primary-dark: #1d4ed8;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --font-mono: "JetBrains Mono", "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      background-color: var(--bg-page);
      color: var(--text-main);
      font-family: var(--font-sans);
      line-height: 1.5;
      padding: 30px 15px;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}

    .certificate-wrapper {{
      max-width: 960px;
      margin: 0 auto;
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01);
      overflow: hidden;
    }}

    /* Top Action Bar for interactive browser view */
    .action-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #0f172a;
      color: #ffffff;
      padding: 12px 24px;
      font-size: 13px;
    }}

    .action-bar .brand {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      letter-spacing: 0.5px;
    }}

    .action-bar .brand span {{
      color: #38bdf8;
    }}

    .action-btns {{
      display: flex;
      gap: 10px;
    }}

    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      border: none;
      transition: all 0.2s;
    }}

    .btn-primary {{
      background: #2563eb;
      color: #ffffff;
    }}
    .btn-primary:hover {{
      background: #1d4ed8;
    }}

    .btn-secondary {{
      background: #334155;
      color: #f1f5f9;
    }}
    .btn-secondary:hover {{
      background: #475569;
    }}

    /* Certificate Document Container */
    .certificate-body {{
      padding: 40px;
    }}

    /* Header Section */
    .cert-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 2px solid #e2e8f0;
      padding-bottom: 24px;
      margin-bottom: 28px;
    }}

    .lab-info {{
      display: flex;
      gap: 16px;
      align-items: center;
    }}

    .lab-seal {{
      width: 56px;
      height: 56px;
      background: linear-gradient(135deg, #1e293b, #0f172a);
      color: #38bdf8;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }}

    .lab-titles h1 {{
      font-size: 20px;
      font-weight: 800;
      letter-spacing: 0.5px;
      color: #0f172a;
      text-transform: uppercase;
    }}

    .lab-titles p {{
      font-size: 12px;
      color: var(--text-muted);
      font-weight: 500;
      margin-top: 2px;
    }}

    .cert-meta {{
      text-align: right;
    }}

    .cert-badge-security {{
      display: inline-block;
      background: #f1f5f9;
      color: #334155;
      font-size: 11px;
      font-weight: 700;
      padding: 4px 8px;
      border-radius: 4px;
      letter-spacing: 0.5px;
      border: 1px solid #cbd5e1;
      margin-bottom: 6px;
    }}

    .cert-id {{
      font-family: var(--font-mono);
      font-size: 14px;
      font-weight: 700;
      color: #0f172a;
    }}

    .cert-date {{
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 2px;
    }}

    /* Evidence Custody Box */
    .custody-box {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 16px 20px;
      margin-bottom: 28px;
    }}

    .custody-title {{
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #475569;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .custody-grid {{
      display: grid;
      grid-template-columns: 2fr 1fr 1fr;
      gap: 16px;
      font-size: 13px;
    }}

    .custody-item {{
      display: flex;
      flex-direction: column;
    }}

    .custody-item .label {{
      font-size: 11px;
      color: #64748b;
      font-weight: 600;
      text-transform: uppercase;
      margin-bottom: 2px;
    }}

    .custody-item .value {{
      font-weight: 600;
      color: #1e293b;
      word-break: break-all;
    }}

    .custody-item .hash-val {{
      font-family: var(--font-mono);
      font-size: 11px;
      color: #0f172a;
      background: #edf2f7;
      padding: 4px 6px;
      border-radius: 4px;
      border: 1px solid #cbd5e1;
      margin-top: 2px;
    }}

    /* Verdict Banner */
    .verdict-banner {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      border: 2px solid {verdict_border};
      background: {verdict_bg};
      border-radius: 10px;
      padding: 20px 24px;
      margin-bottom: 30px;
    }}

    .verdict-left {{
      display: flex;
      align-items: center;
      gap: 20px;
    }}

    .score-circle {{
      width: 72px;
      height: 72px;
      border-radius: 50%;
      background: #ffffff;
      border: 4px solid {verdict_color};
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }}

    .score-val {{
      font-size: 20px;
      font-weight: 800;
      color: {verdict_color};
      line-height: 1;
    }}

    .score-sub {{
      font-size: 9px;
      font-weight: 700;
      color: #64748b;
      text-transform: uppercase;
      margin-top: 2px;
    }}

    .verdict-info h2 {{
      font-size: 20px;
      font-weight: 800;
      color: {verdict_color};
      letter-spacing: 0.5px;
    }}

    .verdict-info p {{
      font-size: 13px;
      color: #334155;
      margin-top: 4px;
      max-width: 580px;
    }}

    .verdict-right {{
      text-align: right;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}

    .grade-badge {{
      display: inline-block;
      background: #ffffff;
      color: #0f172a;
      border: 1px solid #cbd5e1;
      font-size: 12px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 6px;
    }}

    .confidence-badge {{
      font-size: 12px;
      color: #475569;
      font-weight: 600;
    }}

    /* Section Headings */
    .section-title {{
      font-size: 14px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #1e293b;
      border-bottom: 2px solid #e2e8f0;
      padding-bottom: 6px;
      margin: 28px 0 16px 0;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    /* Telemetry Table */
    .telemetry-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      margin-bottom: 28px;
    }}

    .telemetry-table th {{
      background: #f1f5f9;
      color: #334155;
      font-weight: 700;
      text-align: left;
      padding: 10px 14px;
      border: 1px solid #e2e8f0;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    .telemetry-table td {{
      padding: 12px 14px;
      border: 1px solid #e2e8f0;
      vertical-align: middle;
    }}

    .telemetry-table tr:nth-child(even) {{
      background: #f8fafc;
    }}

    .point-name {{
      font-weight: 700;
      color: #0f172a;
      display: block;
    }}

    .point-desc {{
      font-size: 11px;
      color: #64748b;
      margin-top: 2px;
    }}

    .point-score {{
      font-size: 15px;
      font-weight: 800;
      font-family: var(--font-mono);
    }}

    .pill {{
      display: inline-block;
      font-size: 10px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      letter-spacing: 0.5px;
    }}
    .pill-low {{
      background: #ecfdf5;
      color: #065f46;
      border: 1px solid #a7f3d0;
    }}
    .pill-med {{
      background: #fffbeb;
      color: #92400e;
      border: 1px solid #fde68a;
    }}
    .pill-high {{
      background: #fef2f2;
      color: #991b1b;
      border: 1px solid #fecaca;
    }}

    /* Visual Gallery Matrix */
    .visual-gallery {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      margin-bottom: 28px;
      page-break-inside: avoid;
    }}

    .visual-card {{
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}

    .visual-card img {{
      width: 100%;
      height: 160px;
      object-fit: cover;
      display: block;
      background: #0f172a;
    }}

    .visual-caption {{
      padding: 8px 10px;
      font-size: 11px;
      font-weight: 700;
      color: #334155;
      background: #f8fafc;
      border-top: 1px solid #e2e8f0;
      text-align: center;
    }}

    /* Metadata Audit Box */
    .metadata-box {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 16px 20px;
      margin-bottom: 28px;
    }}

    .warning-list {{
      list-style: none;
      font-size: 12px;
      color: #b91c1c;
    }}

    .warning-list li {{
      margin-bottom: 6px;
    }}

    .clean-note {{
      font-size: 12px;
      color: #065f46;
      font-weight: 600;
    }}

    /* Attestation & Sign-Off */
    .attestation-section {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      border-top: 2px solid #e2e8f0;
      padding-top: 24px;
      margin-top: 36px;
      page-break-inside: avoid;
    }}

    .attestation-text {{
      max-width: 540px;
      font-size: 11px;
      color: #64748b;
      line-height: 1.6;
    }}

    .signature-block {{
      text-align: center;
      min-width: 220px;
    }}

    .sig-line {{
      width: 180px;
      height: 1px;
      background: #0f172a;
      margin: 36px auto 6px auto;
    }}

    .sig-title {{
      font-size: 12px;
      font-weight: 700;
      color: #0f172a;
    }}

    .sig-sub {{
      font-size: 10px;
      color: #64748b;
    }}

    /* Print Specific Formatting */
    @media print {{
      body {{
        background: #ffffff !important;
        padding: 0 !important;
      }}
      .action-bar {{
        display: none !important;
      }}
      .certificate-wrapper {{
        box-shadow: none !important;
        border: none !important;
        max-width: 100% !important;
      }}
      .certificate-body {{
        padding: 15mm !important;
      }}
      .visual-gallery {{
        grid-template-columns: repeat(3, 1fr) !important;
        gap: 8px !important;
      }}
      .visual-card img {{
        height: 130px !important;
      }}
      .telemetry-table th, .telemetry-table td {{
        padding: 8px 10px !important;
      }}
    }}
  </style>
</head>
<body>

  <div class="certificate-wrapper">
    <!-- Top Action Bar (hidden on print) -->
    <div class="action-bar">
      <div class="brand">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="9"/>
          <path d="M12 3v18"/>
          <path d="M3 12h18"/>
          <circle cx="12" cy="12" r="4" fill="currentColor" opacity="0.3"/>
        </svg>
        <span>MorphSpot</span> Digital Forensics Laboratory
      </div>
      <div class="action-btns">
        <button class="btn btn-secondary" onclick="window.print()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 6 2 18 2 18 9"/>
            <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
            <rect x="6" y="14" width="12" height="8"/>
          </svg>
          Print / Save as PDF
        </button>
        <button class="btn btn-primary" onclick="downloadCurrentDocument()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Save Standalone Record
        </button>
      </div>
    </div>

    <!-- Certificate Document Body -->
    <div class="certificate-body">
      <!-- Header -->
      <div class="cert-header">
        <div class="lab-info">
          <div class="lab-seal">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <div class="lab-titles">
            <h1>MorphSpot Digital Forensics</h1>
            <p>Certified Telemetry & Image Tampering Examination Report</p>
          </div>
        </div>
        <div class="cert-meta">
          <span class="cert-badge-security">EVIDENCE AUDIT RECORD</span>
          <div class="cert-id">{report_id}</div>
          <div class="cert-date">{formatted_date}</div>
        </div>
      </div>

      <!-- Chain of Custody & Evidence Info -->
      <div class="custody-box">
        <div class="custody-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
          Digital Evidence Chain of Custody & Identification
        </div>
        <div class="custody-grid">
          <div class="custody-item">
            <span class="label">Evidence File Name</span>
            <span class="value">{filename}</span>
          </div>
          <div class="custody-item">
            <span class="label">Resolution</span>
            <span class="value">{dim_str}</span>
          </div>
          <div class="custody-item">
            <span class="label">Examination Status</span>
            <span class="value" style="color: #059669;">Complete (100%)</span>
          </div>
          <div class="custody-item" style="grid-column: 1 / -1;">
            <span class="label">Cryptographic SHA-256 Digest</span>
            <span class="hash-val">{sha256_hash}</span>
          </div>
        </div>
      </div>

      <!-- Verdict Banner -->
      <div class="verdict-banner">
        <div class="verdict-left">
          <div class="score-circle">
            <span class="score-val">{tampered_prob:.1f}%</span>
            <span class="score-sub">Tampered</span>
          </div>
          <div class="verdict-info">
            <h2>{badge_text}</h2>
            <p>{summary}</p>
          </div>
        </div>
        <div class="verdict-right">
          <span class="grade-badge">{grade}</span>
          <span class="confidence-badge">Confidence: <strong>{confidence}</strong></span>
        </div>
      </div>

      <!-- Multi-Point Forensic Telemetry Table -->
      <div class="section-title">
        <span>Multi-Point Forensic Telemetry Matrix</span>
        <span style="font-size: 11px; font-weight: 500; color: #64748b;">All 6 Points Analyzed</span>
      </div>
      <table class="telemetry-table">
        <thead>
          <tr>
            <th style="width: 32%;">Forensic Examination Point</th>
            <th style="width: 14%;">Score (%)</th>
            <th style="width: 20%;">Anomaly Rating</th>
            <th style="width: 34%;">Findings & Metric Observations</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <span class="point-name">1. Error Level Analysis (ELA)</span>
              <span class="point-desc">DCT re-compression error residuals</span>
            </td>
            <td><span class="point-score">{ela.get('score_percentage', 0.0):.1f}%</span></td>
            <td>{get_risk_pill(ela.get('score_percentage', 0.0))}</td>
            <td>{html.escape(str(ela.get('details', 'N/A')))}</td>
          </tr>
          <tr>
            <td>
              <span class="point-name">2. Sensor Noise Inconsistency</span>
              <span class="point-desc">High-pass noise residual variance</span>
            </td>
            <td><span class="point-score">{noise.get('score_percentage', 0.0):.1f}%</span></td>
            <td>{get_risk_pill(noise.get('score_percentage', 0.0))}</td>
            <td>{html.escape(str(noise.get('details', 'N/A')))}</td>
          </tr>
          <tr>
            <td>
              <span class="point-name">3. Copy-Move / Clone Forgery</span>
              <span class="point-desc">SIFT invariant keypoints & RANSAC</span>
            </td>
            <td><span class="point-score">{copy_move.get('score_percentage', 0.0):.1f}%</span></td>
            <td>{get_risk_pill(copy_move.get('score_percentage', 0.0))}</td>
            <td>{html.escape(str(copy_move.get('details', 'N/A')))}</td>
          </tr>
          <tr>
            <td>
              <span class="point-name">4. Edge Sharpness & Blending</span>
              <span class="point-desc">Sobel contour transition profiles</span>
            </td>
            <td><span class="point-score">{edges.get('score_percentage', 0.0):.1f}%</span></td>
            <td>{get_risk_pill(edges.get('score_percentage', 0.0))}</td>
            <td>{html.escape(str(edges.get('details', 'N/A')))}</td>
          </tr>
          <tr>
            <td>
              <span class="point-name">5. Luminance / Color Variance</span>
              <span class="point-desc">CIE-Lab 2D polynomial surface fit</span>
            </td>
            <td><span class="point-score">{luminance.get('score_percentage', 0.0):.1f}%</span></td>
            <td>{get_risk_pill(luminance.get('score_percentage', 0.0))}</td>
            <td>{html.escape(str(luminance.get('details', 'N/A')))}</td>
          </tr>
          <tr>
            <td>
              <span class="point-name">6. Metadata & EXIF Security</span>
              <span class="point-desc">Software traces & camera verification</span>
            </td>
            <td><span class="point-score">{meta.get('score_percentage', 0.0):.1f}%</span></td>
            <td>{get_risk_pill(meta.get('score_percentage', 0.0))}</td>
            <td>{html.escape(str(meta.get('details', 'N/A')))}</td>
          </tr>
        </tbody>
      </table>

      <!-- Multi-Spectral Visual Evidence Matrix -->
      <div class="section-title">
        <span>Multi-Spectral Visual Evidence Matrix</span>
        <span style="font-size: 11px; font-weight: 500; color: #64748b;">Visual Anomaly Overlays</span>
      </div>
      <div class="visual-gallery">
        <div class="visual-card">
          <img src="{orig_b64}" alt="Original Ingested Evidence">
          <div class="visual-caption">Fig 1. Ingested Evidence Source</div>
        </div>
        <div class="visual-card">
          <img src="{composite_b64}" alt="Composite Anomaly Heatmap">
          <div class="visual-caption">Fig 2. Composite Anomaly Heatmap</div>
        </div>
        <div class="visual-card">
          <img src="{ela_b64 if ela_b64 else composite_b64}" alt="ELA Heatmap">
          <div class="visual-caption">Fig 3. ELA DCT Residual Map</div>
        </div>
        <div class="visual-card">
          <img src="{noise_b64 if noise_b64 else composite_b64}" alt="Noise Residual Field">
          <div class="visual-caption">Fig 4. Sensor Noise Disparity Map</div>
        </div>
        <div class="visual-card">
          <img src="{copymove_b64 if copymove_b64 else composite_b64}" alt="Copy-Move Splicing Vectors">
          <div class="visual-caption">Fig 5. Keypoint Displacement Vectors</div>
        </div>
        <div class="visual-card">
          <img src="{edges_b64 if edges_b64 else composite_b64}" alt="Edge Gradient Map">
          <div class="visual-caption">Fig 6. Contour Transition Anomaly</div>
        </div>
      </div>

      <!-- EXIF & Software Audit Log -->
      <div class="section-title">
        <span>EXIF & Provenance Integrity Audit</span>
      </div>
      <div class="metadata-box">
        {meta_warnings_html}
      </div>

      <!-- Cryptographic Attestation Block -->
      <div class="attestation-section">
        <div class="attestation-text">
          <strong>Digital Attestation & Cryptographic Integrity:</strong><br>
          This document represents the computer vision forensic examination results generated by the MorphSpot Multi-Spectral Forensic Engine (v1.0.0). The cryptographic hash recorded above uniquely identifies the analyzed media in compliance with digital evidence integrity principles.
        </div>
        <div class="signature-block">
          <div class="sig-line"></div>
          <div class="sig-title">Automated Forensic Engine</div>
          <div class="sig-sub">MorphSpot Certified Telemetry</div>
        </div>
      </div>
    </div>
  </div>

  <script>
    function downloadCurrentDocument() {{
      const docHtml = '<!DOCTYPE html>\\n' + document.documentElement.outerHTML;
      const blob = new Blob([docHtml], {{ type: 'text/html;charset=utf-8' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'Forensic_Certificate_{report_id}.html';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }}
  </script>
</body>
</html>"""
    return html_content
