#!/bin/bash
# Quick start script for AffiScan on macOS/Linux

echo "==================================="
echo "  AffiScan - Startup Script"
echo "==================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "[ERROR] File .env not found!"
    echo ""
    echo "Please create .env file from .env.example:"
    echo "  cp .env.example .env"
    echo ""
    echo "Then edit .env and add your Google API keys"
    echo ""
    exit 1
fi

# Check if venv exists
if [ ! -d venv ]; then
    echo "[INFO] Virtual environment not found. Creating..."
    python3 -m venv venv
    echo "[INFO] Virtual environment created"
fi

# Activate virtual environment
echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "[INFO] Installing dependencies..."
pip install -r requirements.txt

# Run Streamlit
echo "[INFO] Starting AffiScan..."
echo ""
echo "App will open at: http://localhost:8501"
echo ""
streamlit run ads.py
