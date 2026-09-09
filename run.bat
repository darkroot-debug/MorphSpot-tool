@echo off
title MorphSpot Image Forensics Engine
echo ========================================================
echo        MorphSpot - Digital Image Forensics Engine
echo ========================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10 or newer from https://www.python.org/
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [SETUP] Creating Python virtual environment (venv)...
    python -m venv venv
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Install / Update dependencies
echo [SETUP] Checking and installing dependencies...
pip install -r requirements.txt

:: Launch the application
echo.
echo ========================================================
echo [RUNNING] Starting MorphSpot Web Dashboard...
echo Local Server: http://127.0.0.1:8000
echo API Docs:     http://127.0.0.1:8000/docs
echo ========================================================
echo.

:: Open browser automatically
start http://127.0.0.1:8000

:: Run Uvicorn server
python -m uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload

pause
