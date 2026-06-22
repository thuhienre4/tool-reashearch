@echo off
REM Quick start script for AffiScan on Windows

echo ===================================
echo   AffiScan - Startup Script
echo ===================================
echo.

REM Check if .env file exists
if not exist .env (
    echo [ERROR] File .env not found!
    echo.
    echo Please create .env file from .env.example:
    echo   copy .env.example .env
    echo.
    echo Then edit .env and add your Google API keys
    echo.
    pause
    exit /b 1
)

REM Check if venv exists
if not exist venv (
    echo [INFO] Virtual environment not found. Creating...
    python -m venv venv
    echo [INFO] Virtual environment created
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/upgrade dependencies
echo [INFO] Installing dependencies...
pip install -r requirements.txt

REM Run Streamlit
echo [INFO] Starting AffiScan...
echo.
echo App will open at: http://localhost:8501
echo.
streamlit run ads.py

pause
