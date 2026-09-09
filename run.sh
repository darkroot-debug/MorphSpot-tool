#!/usr/bin/env bash
# MorphSpot One-Click Launcher for Linux & macOS
set -e

echo "========================================================"
echo "       MorphSpot - Digital Image Forensics Engine       "
echo "========================================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.10+."
    exit 1
fi

# Create Virtual Environment if missing
if [ ! -d "venv" ]; then
    echo "[SETUP] Creating virtual environment..."
    python3 -m venv venv
fi

# Activate Environment
source venv/bin/activate

# Install Dependencies
echo "[SETUP] Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# Start Server
echo ""
echo "========================================================"
echo "[RUNNING] Starting MorphSpot Web Application..."
echo "Dashboard: http://127.0.0.1:8000"
echo "API Docs:  http://127.0.0.1:8000/docs"
echo "========================================================"
echo ""

# Open browser if possible
if command -v xdg-open &> /dev/null; then
    xdg-open http://127.0.0.1:8000 &
elif command -v open &> /dev/null; then
    open http://127.0.0.1:8000 &
fi

python3 -m uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
