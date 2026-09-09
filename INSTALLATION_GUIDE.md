# MorphSpot - Complete Setup & Deployment Guide

This guide provides instructions to run **MorphSpot** on another computer (Windows, macOS, Linux) or deploy it live to the cloud / production server.

---

## 💻 System Prerequisites

- **Python:** Version `3.10`, `3.11`, `3.12`, `3.13`, or `3.14`
- **RAM:** Minimum 2 GB (4 GB recommended for large megapixel images)
- **OS:** Windows 10/11, macOS (Intel/Apple Silicon), or Linux (Ubuntu, Debian, CentOS, Arch)

---

## 🚀 Option 1: Running on Windows (Easiest)

### Method A: One-Click Launcher (Double-Click)
1. Extract the `MorphSpot_Image_Forensics.zip` or `image_forensics.zip` folder.
2. Double-click **`run.bat`**.
3. It will automatically:
   - Create a virtual environment (`venv`)
   - Install all required libraries (`requirements.txt`)
   - Start the server and open **`http://127.0.0.1:8000`** in your default browser.

### Method B: Manual PowerShell / CMD
1. Open PowerShell or Command Prompt inside the extracted folder:
   ```powershell
   # 1. Create a virtual environment
   python -m venv venv

   # 2. Activate virtual environment
   .\venv\Scripts\activate

   # 3. Install dependencies
   pip install -r requirements.txt

   # 4. Start the MorphSpot server
   python -m uvicorn app.api:app --host 127.0.0.1 --port 8000 --reload
   ```
2. Open your browser at **`http://127.0.0.1:8000`**.

---

## 🍎 Option 2: Running on macOS & Linux

1. Open Terminal inside the extracted folder.
2. Make `run.sh` executable and run it:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```
   *Or run manually:*
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   python3 -m uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
   ```
3. Open **`http://localhost:8000`** in your browser.

> **Note for Linux headless servers:** If OpenCV complains about missing GL libraries, install:
> `sudo apt update && sudo apt install -y libgl1 libglib2.0-0`

---

## 🐳 Option 3: Running with Docker (Recommended for Servers)

MorphSpot includes a production-ready `Dockerfile` and `docker-compose.yml`.

### Using Docker Compose (1 Command):
```bash
docker-compose up -d --build
```
- Access Dashboard: `http://<your-server-ip>:8000`
- Check logs: `docker-compose logs -f`
- Stop container: `docker-compose down`

### Using Docker CLI:
```bash
# Build image
docker build -t morphspot .

# Run container
docker run -d -p 8000:8000 --name morphspot-app morphspot
```

---

## ☁️ Option 4: Deploying Live to the Cloud (Free / Cheap Cloud Hosting)

### A. Deploy to Render (Free / Easy)
1. Push this folder to a GitHub repository.
2. Create a free account at [render.com](https://render.com/).
3. Click **New +** &rarr; **Web Service**.
4. Connect your GitHub repository.
5. Set:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.api:app --host 0.0.0.0 --port $PORT`
6. Click **Create Web Service** &rarr; Your app will be live with a public HTTPS URL (e.g. `https://morphspot.onrender.com`).

### B. Deploy to Railway.app
1. Go to [railway.app](https://railway.app/).
2. Click **New Project** &rarr; **Deploy from GitHub repo** or upload directory.
3. Railway detects the `Dockerfile` or `requirements.txt` automatically and deploys it live.

### C. Deploy to Ubuntu VPS (DigitalOcean, AWS EC2, Linode, Hetzner)
1. SSH into your VPS:
   ```bash
   sudo apt update && sudo apt install -y python3-pip python3-venv git libgl1 libglib2.0-0
   git clone <your-repo-url> /opt/morphspot
   cd /opt/morphspot
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Create a systemd service (`/etc/systemd/system/morphspot.service`):
   ```ini
   [Unit]
   Description=MorphSpot Image Forensics Server
   After=network.target

   [Service]
   User=root
   WorkingDirectory=/opt/morphspot
   ExecStart=/opt/morphspot/venv/bin/uvicorn app.api:app --host 0.0.0.0 --port 8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
3. Start the service:
   ```bash
   sudo systemctl enable --now morphspot
   ```

---

## 🧪 Verification & Running Tests

To verify that all computer vision algorithms, certificate generators, and REST API endpoints are functioning on the new machine:

```bash
python -m unittest discover tests
```
*Expected Output:*
```text
Ran 13 tests in ~5s
OK
```

---

## 📁 Key Project Files Overview

```
image_forensics/
├── run.bat                 # Windows one-click launcher
├── run.sh                  # Linux/Mac launcher
├── Dockerfile              # Docker container definition
├── docker-compose.yml      # Single-command Docker Compose setup
├── requirements.txt        # Python library dependencies
├── README.md               # Technical project documentation
├── INSTALLATION_GUIDE.md   # This setup and deployment guide
├── cli.py                  # Standalone CLI analysis tool
├── app/
│   ├── api.py              # FastAPI REST endpoints (/analyze, /certificate, /health)
│   ├── engine.py           # Master Multi-Modal Fusion Engine
│   ├── config.py           # Config parameters and algorithm thresholds
│   ├── modules/            # 6 Forensic Detection Algorithms:
│   │   ├── ela.py          # Error Level Analysis
│   │   ├── noise.py        # Sensor Noise Residuals & MAD Z-Scores
│   │   ├── copy_move.py    # SIFT/ORB Keypoint Clustering & RANSAC
│   │   ├── edges.py        # Sobel Contour Gradients & Blending
│   │   ├── luminance.py    # CIE-Lab Illumination Surface Fitting
│   │   └── metadata.py     # EXIF/XMP/IPTC Software Signature Audit
│   ├── utils/
│   │   ├── image_io.py     # Image loading, preprocessing & SHA-256
│   │   ├── visualizer.py   # Heatmap & overlay encoders
│   │   └── reporter.py     # Standalone PDF/HTML Certificate Generator
│   └── static/             # Web UI Dashboard (HTML5/CSS3/Vanilla JS)
└── tests/                  # Unit and integration test suite
```
