/**
 * MorphSpot Interactive Forensic Dashboard Client
 */
document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const loadingOverlay = document.getElementById('loadingOverlay');
  const emptyPlaceholder = document.getElementById('emptyPlaceholder');
  const resultsContainer = document.getElementById('resultsContainer');
  
  // Viewer Elements
  const viewOriginal = document.getElementById('viewOriginal');
  const viewMask = document.getElementById('viewMask');
  const opacitySlider = document.getElementById('opacitySlider');
  const opacityVal = document.getElementById('opacityVal');
  const layerTabs = document.querySelectorAll('.layer-tab');
  const modeBtns = {
    blend: document.getElementById('modeBlendBtn'),
    split: document.getElementById('modeSplitBtn'),
    original: document.getElementById('modeOriginalBtn'),
    mask: document.getElementById('modeMaskBtn')
  };

  // Verdict & Metric Elements
  const verdictBanner = document.getElementById('verdictBanner');
  const scoreRingProgress = document.getElementById('scoreRingProgress');
  const scorePercentVal = document.getElementById('scorePercentVal');
  const verdictLabel = document.getElementById('verdictLabel');
  const verdictSummary = document.getElementById('verdictSummary');
  const confidenceVal = document.getElementById('confidenceVal');
  const filenameVal = document.getElementById('filenameVal');

  // JSON & Certificate Elements
  const jsonOutput = document.getElementById('jsonOutput');
  const copyJsonBtn = document.getElementById('copyJsonBtn');
  const downloadJsonBtn = document.getElementById('downloadJsonBtn');
  const viewCertBtnBanner = document.getElementById('viewCertBtnBanner');
  const downloadCertBtn = document.getElementById('downloadCertBtn');
  const certModal = document.getElementById('certModal');
  const certModalCloseBtn = document.getElementById('certModalCloseBtn');
  const certModalPrintBtn = document.getElementById('certModalPrintBtn');
  const certModalDownloadBtn = document.getElementById('certModalDownloadBtn');
  const certPreviewIframe = document.getElementById('certPreviewIframe');

  // Active State
  let currentReport = null;
  let activeLayer = 'composite';
  let viewMode = 'blend';

  // --- Drag and Drop Handlers ---
  ['dragenter', 'dragover'].forEach(name => {
    dropzone.addEventListener(name, (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(name => {
    dropzone.addEventListener(name, (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      processImageFile(files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      processImageFile(e.target.files[0]);
    }
  });

  // Preset Buttons
  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const type = btn.getAttribute('data-type');
      loadPresetImage(type);
    });
  });

  // --- API Analysis Function ---
  async function processImageFile(file) {
    showLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('include_visuals', 'true');

    try {
      const response = await fetch('/api/v1/analyze', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }

      const report = await response.json();
      currentReport = report;
      renderReport(report);
    } catch (err) {
      alert(`Forensic analysis failed: ${err.message}`);
    } finally {
      showLoading(false);
    }
  }

  function showLoading(isLoading) {
    if (isLoading) {
      loadingOverlay.classList.remove('hidden');
      emptyPlaceholder.classList.add('hidden');
      resultsContainer.classList.add('hidden');
    } else {
      loadingOverlay.classList.add('hidden');
    }
  }

  // --- Render Report UI ---
  function renderReport(report) {
    emptyPlaceholder.classList.add('hidden');
    resultsContainer.classList.remove('hidden');

    const score = report.tampered_probability_percentage;
    const verdict = report.verdict;
    const confidence = report.confidence_level;
    const filename = report.filename;
    const breakdown = report.forensic_breakdown;

    // 1. Update Verdict Banner
    scorePercentVal.textContent = `${score}%`;
    verdictLabel.textContent = verdict;
    verdictSummary.textContent = report.summary;
    confidenceVal.textContent = confidence;
    filenameVal.textContent = filename;

    // Update Circle Ring Progress
    const radius = 36;
    const circumference = 2 * Math.PI * radius; // ~226
    const offset = circumference - (score / 100) * circumference;
    scoreRingProgress.style.strokeDashoffset = offset;

    // Banner Color Class
    verdictBanner.className = 'verdict-banner';
    if (score < 30) {
      verdictBanner.classList.add('verdict-authentic');
      scoreRingProgress.style.stroke = '#10b981';
    } else if (score <= 65) {
      verdictBanner.classList.add('verdict-suspicious');
      scoreRingProgress.style.stroke = '#f59e0b';
    } else {
      verdictBanner.classList.add('verdict-tampered');
      scoreRingProgress.style.stroke = '#ef4444';
    }

    // 2. Setup Images in Viewer
    if (report.visual_breakdown && report.visual_breakdown.original_base64) {
      viewOriginal.src = report.visual_breakdown.original_base64;
    } else {
      viewOriginal.src = report.annotated_mask_base64;
    }
    updateActiveMaskLayer();

    // 3. Render Breakdown Cards
    renderMetricCard('ela', breakdown.ela_analysis, '%');
    renderMetricCard('noise', breakdown.noise_consistency, '%');
    renderMetricCard('copy', breakdown.copy_move_detection, '%');
    renderMetricCard('edge', breakdown.edge_sharpness_inconsistency, '%');
    renderMetricCard('lum', breakdown.luminance_gradient_variance, '%');
    renderMetadataCard(breakdown.metadata_analysis);

    // 4. Render JSON Box
    jsonOutput.textContent = JSON.stringify(report, null, 2);
  }

  function getPillClass(score) {
    if (score >= 65) return 'score-pill high';
    if (score >= 30) return 'score-pill medium';
    return 'score-pill low';
  }

  function renderMetricCard(key, data, unit) {
    if (!data) return;
    const badge = document.getElementById(`${key}ScoreBadge`);
    const details = document.getElementById(`${key}Details`);
    const subtags = document.getElementById(`${key}Subtags`);

    const score = data.score_percentage || 0;
    badge.textContent = `${score}${unit}`;
    badge.className = getPillClass(score);
    details.textContent = data.details || '';

    // Render metric subtags if present
    subtags.innerHTML = '';
    if (data.metrics) {
      Object.entries(data.metrics).forEach(([mKey, mVal]) => {
        const span = document.createElement('span');
        span.className = 'metric-subtag';
        span.textContent = `${mKey}: ${mVal}`;
        subtags.appendChild(span);
      });
    }
  }

  function renderMetadataCard(meta) {
    if (!meta) return;
    const badge = document.getElementById('metaScoreBadge');
    const details = document.getElementById('metaDetails');
    const container = document.getElementById('metaTagsList');

    if (meta.flagged) {
      badge.textContent = 'Flagged';
      badge.className = 'score-pill high';
    } else if (meta.has_exif) {
      badge.textContent = 'Verified EXIF';
      badge.className = 'score-pill low';
    } else {
      badge.textContent = 'No EXIF';
      badge.className = 'score-pill medium';
    }

    details.textContent = meta.details || '';
    container.innerHTML = '';

    if (meta.warnings && meta.warnings.length > 0) {
      meta.warnings.forEach(w => {
        const span = document.createElement('span');
        span.className = 'meta-tag-pill warning';
        span.textContent = `⚠️ ${w}`;
        container.appendChild(span);
      });
    }

    if (meta.software_detected && meta.software_detected !== 'None') {
      const span = document.createElement('span');
      span.className = 'meta-tag-pill warning';
      span.textContent = `Software: ${meta.software_detected}`;
      container.appendChild(span);
    }
  }

  // --- Visual Layer Switching ---
  function updateActiveMaskLayer() {
    if (!currentReport) return;
    const visuals = currentReport.visual_breakdown || {};
    
    let maskSrc = currentReport.annotated_mask_base64;
    if (activeLayer === 'ela' && visuals.ela_heatmap_base64) {
      maskSrc = visuals.ela_heatmap_base64;
    } else if (activeLayer === 'noise' && visuals.noise_heatmap_base64) {
      maskSrc = visuals.noise_heatmap_base64;
    } else if (activeLayer === 'copymove' && visuals.copy_move_annotated_base64) {
      maskSrc = visuals.copy_move_annotated_base64;
    } else if (activeLayer === 'edges' && visuals.edge_heatmap_base64) {
      maskSrc = visuals.edge_heatmap_base64;
    } else if (activeLayer === 'luminance' && visuals.luminance_heatmap_base64) {
      maskSrc = visuals.luminance_heatmap_base64;
    }

    viewMask.src = maskSrc;
  }

  layerTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      layerTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      activeLayer = tab.getAttribute('data-layer');
      updateActiveMaskLayer();
    });
  });

  // --- Viewer Controls ---
  opacitySlider.addEventListener('input', (e) => {
    const val = e.target.value;
    opacityVal.textContent = `${val}%`;
    if (viewMode === 'blend') {
      viewMask.style.opacity = val / 100;
    }
  });

  function setViewMode(mode) {
    viewMode = mode;
    Object.values(modeBtns).forEach(btn => btn.classList.remove('active'));
    modeBtns[mode].classList.add('active');

    if (mode === 'blend') {
      viewOriginal.style.display = 'block';
      viewMask.style.display = 'block';
      viewMask.style.opacity = opacitySlider.value / 100;
    } else if (mode === 'original') {
      viewOriginal.style.display = 'block';
      viewMask.style.display = 'none';
    } else if (mode === 'mask') {
      viewOriginal.style.display = 'none';
      viewMask.style.display = 'block';
      viewMask.style.opacity = '1';
    }
  }

  modeBtns.blend.addEventListener('click', () => setViewMode('blend'));
  modeBtns.original.addEventListener('click', () => setViewMode('original'));
  modeBtns.mask.addEventListener('click', () => setViewMode('mask'));

  // --- JSON Copy & Download ---
  copyJsonBtn.addEventListener('click', () => {
    if (currentReport) {
      navigator.clipboard.writeText(JSON.stringify(currentReport, null, 2));
      copyJsonBtn.innerHTML = `✓ Copied!`;
      setTimeout(() => {
        copyJsonBtn.innerHTML = `Copy JSON`;
      }, 2000);
    }
  });

  downloadJsonBtn.addEventListener('click', () => {
    if (currentReport) {
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(currentReport, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `forensic_report_${Date.now()}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    }
  });

  // --- Forensic Audit Certificate Functions ---
  async function openCertificateModal() {
    if (!currentReport) return;
    certModal.classList.remove('hidden');
    certPreviewIframe.srcdoc = `<!DOCTYPE html><html><body style="font-family: -apple-system, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #f8fafc; color: #334155;"><div style="text-align: center;"><div style="font-size: 28px; margin-bottom: 12px;">⏳</div><h3>Compiling Official Forensic Audit Certificate...</h3><p style="font-size: 13px; color: #64748b;">Synthesizing cryptographic SHA-256 hash and multi-spectral telemetry</p></div></body></html>`;

    try {
      const response = await fetch('/api/v1/report/certificate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentReport)
      });
      if (!response.ok) throw new Error(`Server returned error ${response.status}`);
      const htmlText = await response.text();
      certPreviewIframe.srcdoc = htmlText;
    } catch (err) {
      alert("Failed to render certificate: " + err.message);
      certModal.classList.add('hidden');
    }
  }

  function closeCertificateModal() {
    certModal.classList.add('hidden');
  }

  function printCertificate() {
    if (certPreviewIframe && certPreviewIframe.contentWindow) {
      certPreviewIframe.contentWindow.focus();
      certPreviewIframe.contentWindow.print();
    }
  }

  async function downloadCertificateFile() {
    if (!currentReport) return;
    try {
      const response = await fetch('/api/v1/report/certificate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentReport)
      });
      if (!response.ok) throw new Error(`Server returned error ${response.status}`);
      const blob = await response.blob();
      const reportId = currentReport.report_id || 'AUDIT';
      const cleanFilename = (currentReport.filename || 'evidence').replace(/[^a-zA-Z0-9_-]/g, '_');
      const downloadAnchor = document.createElement('a');
      const url = URL.createObjectURL(blob);
      downloadAnchor.href = url;
      downloadAnchor.download = `Forensic_Certificate_${cleanFilename}_${reportId}.html`;
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      document.body.removeChild(downloadAnchor);
      URL.revokeObjectURL(url);
    } catch (err) {
      alert("Failed to download certificate: " + err.message);
    }
  }

  const headerCertBtn = document.getElementById('headerCertBtn');
  const sidebarDownloadCertBtn = document.getElementById('sidebarDownloadCertBtn');
  const sidebarDownloadJsonBtn = document.getElementById('sidebarDownloadJsonBtn');
  const bigDownloadCertBtn = document.getElementById('bigDownloadCertBtn');
  const bigDownloadJsonBtn = document.getElementById('bigDownloadJsonBtn');

  function downloadJsonFile() {
    if (currentReport) {
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(currentReport, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `forensic_report_${Date.now()}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } else {
      alert("Please upload and analyze an image first.");
    }
  }

  if (headerCertBtn) {
    headerCertBtn.addEventListener('click', () => {
      if (currentReport) openCertificateModal();
      else alert("Please upload and analyze an image first.");
    });
  }
  if (sidebarDownloadCertBtn) {
    sidebarDownloadCertBtn.addEventListener('click', () => {
      if (currentReport) openCertificateModal();
      else alert("Please upload and analyze an image first.");
    });
  }
  if (sidebarDownloadJsonBtn) {
    sidebarDownloadJsonBtn.addEventListener('click', downloadJsonFile);
  }
  if (bigDownloadCertBtn) {
    bigDownloadCertBtn.addEventListener('click', openCertificateModal);
  }
  if (bigDownloadJsonBtn) {
    bigDownloadJsonBtn.addEventListener('click', downloadJsonFile);
  }
  if (viewCertBtnBanner) {
    viewCertBtnBanner.addEventListener('click', openCertificateModal);
  }
  if (downloadCertBtn) {
    downloadCertBtn.addEventListener('click', openCertificateModal);
  }
  if (certModalCloseBtn) {
    certModalCloseBtn.addEventListener('click', closeCertificateModal);
  }
  if (certModalPrintBtn) {
    certModalPrintBtn.addEventListener('click', printCertificate);
  }
  if (certModalDownloadBtn) {
    certModalDownloadBtn.addEventListener('click', downloadCertificateFile);
  }
  if (certModal) {
    certModal.addEventListener('click', (e) => {
      if (e.target === certModal) closeCertificateModal();
    });
  }
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && certModal && !certModal.classList.contains('hidden')) {
      closeCertificateModal();
    }
  });

  // --- Preset Images Loader ---
  async function loadPresetImage(presetType) {
    const fileMap = {
      'sample_dslr': { url: '/static/samples/1_authentic_dslr_landscape.jpg', name: '1_authentic_dslr_landscape.jpg' },
      'sample_iphone': { url: '/static/samples/2_authentic_iphone_portrait.jpg', name: '2_authentic_iphone_portrait.jpg' },
      'sample_spliced_moon': { url: '/static/samples/3_spliced_foreign_object.jpg', name: '3_spliced_foreign_object.jpg' },
      'sample_copymove_stamp': { url: '/static/samples/copy_move_sample.jpg', name: 'copy_move_sample.jpg' },
      'sample_photoshop_skin': { url: '/static/samples/5_retouched_photoshop_portrait.jpg', name: '5_retouched_photoshop_portrait.jpg' }
    };

    const target = fileMap[presetType];
    if (!target) return;

    try {
      showLoading(true);
      const res = await fetch(target.url);
      const blob = await res.blob();
      const file = new File([blob], target.name, { type: blob.type || 'image/jpeg' });
      processImageFile(file);
    } catch (err) {
      alert(`Failed to load preset: ${err.message}`);
      showLoading(false);
    }
  }
});
